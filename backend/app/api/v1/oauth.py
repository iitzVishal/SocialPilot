import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.enums import SocialPlatform
from app.schemas.social_account import (
    SocialAccountCreate,
    SocialAccountResponse,
    FacebookInstagramAccount,
    FacebookPageItem,
    FacebookPagesResponse,
    FacebookConnectPageRequest,
    FacebookConnectPageResponse,
)
from app.services import social_account_service
from app.services.team_service import TeamService
from app.integrations import get_platform_adapter
from app.core.config import settings
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory fallback state storage for environments without Redis
_IN_MEMORY_STATE_CACHE: Dict[str, Dict[str, Any]] = {}
_IN_MEMORY_SESSION_CACHE: Dict[str, Dict[str, Any]] = {}

PROVIDER_KEY_MAP = {
    "facebook": SocialPlatform.FACEBOOK,
    "instagram": SocialPlatform.INSTAGRAM,
    "linkedin": SocialPlatform.LINKEDIN,
    "x": SocialPlatform.TWITTER,
    "twitter": SocialPlatform.TWITTER,
    "youtube": SocialPlatform.YOUTUBE,
    "pinterest": SocialPlatform.PINTEREST,
}


def _get_provider_redirect_uri(provider: str) -> str:
    if provider == "facebook":
        return settings.META_REDIRECT_URI
    elif provider == "instagram":
        # Instagram uses Facebook Login flow, so callback routes to the same facebook callback
        return settings.META_REDIRECT_URI
    elif provider == "linkedin":
        return settings.LINKEDIN_REDIRECT_URI
    elif provider in ("x", "twitter"):
        return settings.X_REDIRECT_URI
    elif provider == "youtube":
        return settings.GOOGLE_REDIRECT_URI
    elif provider == "pinterest":
        return settings.PINTEREST_REDIRECT_URI
    raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: '{provider}'")


def _verify_provider_configured(provider: str):
    if provider in ("facebook", "instagram"):
        if not settings.META_CLIENT_ID or not settings.META_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instagram/Meta OAuth is not configured. Set META_CLIENT_ID, META_CLIENT_SECRET and META_REDIRECT_URI in backend/.env"
            )
    elif provider == "linkedin":
        if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn OAuth is not configured. Set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET and LINKEDIN_REDIRECT_URI in backend/.env"
            )
    elif provider in ("x", "twitter"):
        if not settings.X_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X/Twitter OAuth is not configured. Set X_CLIENT_ID, X_CLIENT_SECRET and X_REDIRECT_URI in backend/.env"
            )
    elif provider == "youtube":
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google/YouTube OAuth is not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI in backend/.env"
            )
    elif provider == "pinterest":
        if not settings.PINTEREST_CLIENT_ID or not settings.PINTEREST_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pinterest OAuth is not configured. Set PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET and PINTEREST_REDIRECT_URI in backend/.env"
            )


async def _save_oauth_state(state: str, payload: Dict[str, Any]):
    """Persist OAuth state with 10-minute expiration."""
    try:
        redis = get_redis_client()
        if redis is not None:
            await redis.set(f"oauth_state:{state}", json.dumps(payload), ex=600)
    except Exception as e:
        logger.warning(f"Redis state save fallback to memory: {e}")

    _IN_MEMORY_STATE_CACHE[state] = payload


async def _retrieve_and_delete_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """
    Atomically retrieve and delete OAuth state so it can only be consumed once.
    Rejects expired states.
    """
    payload = None
    try:
        redis = get_redis_client()
        if redis is not None:
            raw = await redis.get(f"oauth_state:{state}")
            if raw:
                payload = json.loads(raw)
                await redis.delete(f"oauth_state:{state}")
    except Exception as e:
        logger.warning(f"Redis state retrieval error: {e}")

    # Remove from in-memory cache as well
    mem_payload = _IN_MEMORY_STATE_CACHE.pop(state, None)
    if not payload:
        payload = mem_payload

    if not payload:
        return None

    # Check expiration timestamp
    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"OAuth state {state} has expired ({expires_at_str})")
                return None
        except Exception:
            pass

    return payload


async def _save_oauth_session(session_token: str, payload: Dict[str, Any]):
    """Persist temporary page selection OAuth session with 10-minute TTL."""
    try:
        redis = get_redis_client()
        if redis is not None:
            await redis.set(f"oauth_session:{session_token}", json.dumps(payload), ex=600)
    except Exception as e:
        logger.warning(f"Redis session save fallback to memory: {e}")

    _IN_MEMORY_SESSION_CACHE[session_token] = payload


async def _get_oauth_session(session_token: str) -> Optional[Dict[str, Any]]:
    """Retrieve OAuth page selection session and enforce expiration check."""
    payload = None
    try:
        redis = get_redis_client()
        if redis is not None:
            raw = await redis.get(f"oauth_session:{session_token}")
            if raw:
                payload = json.loads(raw)
    except Exception as e:
        logger.warning(f"Redis session retrieval error: {e}")

    if not payload and session_token in _IN_MEMORY_SESSION_CACHE:
        payload = _IN_MEMORY_SESSION_CACHE.get(session_token)

    if not payload:
        return None

    # Validate expiration
    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                await _delete_oauth_session(session_token)
                return None
        except Exception:
            pass

    return payload


async def _delete_oauth_session(session_token: str):
    """Purge temporary OAuth page selection session."""
    try:
        redis = get_redis_client()
        if redis is not None:
            await redis.delete(f"oauth_session:{session_token}")
    except Exception as e:
        logger.warning(f"Redis session deletion error: {e}")

    _IN_MEMORY_SESSION_CACHE.pop(session_token, None)


@router.get("/{provider}/authorize", summary="Generate platform OAuth authorization URL")
async def authorize_oauth(
    provider: str,
    team_id: Optional[int] = Query(None, description="Optional target team workspace ID"),
    redirect: bool = Query(False, description="If True, issues HTTP 307 redirect directly to provider"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    provider_clean = provider.lower()
    if provider_clean not in PROVIDER_KEY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: '{provider}'. Supported: instagram, facebook, linkedin, x, youtube, pinterest."
        )

    # Check provider credentials configured
    _verify_provider_configured(provider_clean)

    # Determine and verify the target authorized team/workspace
    resolved_team_id = team_id
    if resolved_team_id is not None:
        # Enforce team access: user must be an owner or member of this team
        TeamService.get_team_by_id(db, resolved_team_id, current_user)
    else:
        # Resolve default team for user if available
        user_teams = TeamService.get_teams_for_user(db, current_user)
        if user_teams:
            resolved_team_id = user_teams[0].id

    # Generate cryptographically secure unique state & nonce
    state_token = secrets.token_urlsafe(32)
    nonce = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=600)

    state_payload = {
        "state": state_token,
        "nonce": nonce,
        "user_id": current_user.id,
        "team_id": resolved_team_id,
        "provider": provider_clean,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    await _save_oauth_state(state_token, state_payload)

    platform_enum = PROVIDER_KEY_MAP[provider_clean]
    adapter = get_platform_adapter(platform_enum)
    redirect_uri = _get_provider_redirect_uri(provider_clean)
    auth_url = adapter.get_authorization_url(state=state_token, redirect_uri=redirect_uri)

    if redirect:
        return RedirectResponse(url=auth_url, status_code=307)

    return {
        "authorization_url": auth_url,
        "state": state_token,
        "provider": provider_clean
    }


@router.get("/facebook/pages", response_model=FacebookPagesResponse, summary="Get Facebook Pages available in OAuth session")
async def get_facebook_pages(
    session_token: str = Query(..., description="OAuth session token from callback redirect"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve Facebook Pages available from the current Meta OAuth session.
    Enforces user isolation: session must belong to current authenticated user.
    Never exposes page access tokens or Meta secrets.
    """
    session_data = await _get_oauth_session(session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth session has expired or is invalid. Please start the Facebook connection again."
        )

    if session_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this OAuth session is forbidden."
        )

    if session_data.get("provider") != "facebook":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth session provider."
        )

    session_team_id = session_data.get("team_id")
    if session_team_id is not None:
        TeamService.get_team_by_id(db, session_team_id, current_user)

    safe_pages = []
    for p in session_data.get("pages", []):
        ig = p.get("instagram_account")
        ig_schema = None
        if ig and isinstance(ig, dict):
            ig_schema = FacebookInstagramAccount(
                id=str(ig.get("id")),
                username=ig.get("username"),
                name=ig.get("name"),
                profile_picture_url=ig.get("profile_picture_url")
            )
        safe_pages.append(
            FacebookPageItem(
                page_id=str(p.get("page_id")),
                name=p.get("name", "Facebook Page"),
                category=p.get("category"),
                picture_url=p.get("picture_url"),
                has_instagram=bool(ig),
                instagram_account=ig_schema
            )
        )

    return FacebookPagesResponse(pages=safe_pages)


@router.post("/facebook/connect-page", response_model=FacebookConnectPageResponse, summary="Connect selected Facebook Page and optional Instagram account")
async def connect_facebook_page(
    body: FacebookConnectPageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Connect a user-selected Facebook Page from the active OAuth session.
    Optionally connects the linked Instagram Professional/Business account.
    Access tokens are securely encrypted before database persistence.
    """
    session_data = await _get_oauth_session(body.session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth session has expired or is invalid. Please connect Facebook again."
        )

    if session_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this OAuth session is forbidden."
        )

    if session_data.get("provider") != "facebook":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth session provider."
        )

    # Enforce server-side authoritative team_id from OAuth session
    effective_team_id = session_data.get("team_id")
    if body.team_id is not None and effective_team_id is not None and body.team_id != effective_team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Target team ID does not match the authorized OAuth session."
        )

    if effective_team_id is not None:
        TeamService.get_team_by_id(db, effective_team_id, current_user)

    pages = session_data.get("pages", [])
    selected_page = next((p for p in pages if str(p.get("page_id")) == str(body.page_id)), None)
    if not selected_page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facebook Page '{body.page_id}' was not found in the current OAuth session."
        )

    # Connect Facebook Page
    page_token = selected_page.get("page_access_token") or session_data.get("user_access_token")
    fb_account_in = SocialAccountCreate(
        platform=SocialPlatform.FACEBOOK,
        account_identifier=str(selected_page["page_id"]),
        account_name=selected_page.get("name", "Facebook Page"),
        access_token=page_token,
        refresh_token=None,
        token_expires_at=None,
        platform_permissions={
            "account_type": "PAGE",
            "page_id": str(selected_page["page_id"]),
            "category": selected_page.get("category"),
            "picture_url": selected_page.get("picture_url"),
            "publish_posts": True,
            "read_insights": True,
            "manage_pages": True
        },
        team_id=effective_team_id
    )
    fb_account = social_account_service.connect_account(db, current_user, fb_account_in)
    # Automatic initial synchronization for newly connected Facebook Page
    try:
        social_account_service.synchronize_account(db, current_user, fb_account.id)
        db.refresh(fb_account)
    except Exception as e:
        logger.warning(f"Initial sync for Facebook Page {fb_account.id} failed: {e}")

    # If user opted to connect linked Instagram Professional account
    ig_account = None
    if body.connect_instagram:
        ig_info = selected_page.get("instagram_account")
        if not ig_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An Instagram Professional/Business account is not connected to this Facebook Page."
            )

        ig_account_in = SocialAccountCreate(
            platform=SocialPlatform.INSTAGRAM,
            account_identifier=str(ig_info["id"]),
            account_name=ig_info.get("username") or f"ig_{ig_info['id']}",
            access_token=page_token,
            refresh_token=None,
            token_expires_at=None,
            platform_permissions={
                "account_type": "BUSINESS",
                "instagram_id": str(ig_info["id"]),
                "username": ig_info.get("username"),
                "name": ig_info.get("name"),
                "profile_picture_url": ig_info.get("profile_picture_url"),
                "facebook_page_id": str(selected_page["page_id"]),
                "publish_photos": True,
                "publish_reels": True,
                "read_analytics": True
            },
            team_id=effective_team_id
        )
        ig_account = social_account_service.connect_account(db, current_user, ig_account_in)
        # Automatic initial synchronization for linked Instagram account
        try:
            social_account_service.synchronize_account(db, current_user, ig_account.id)
            db.refresh(ig_account)
        except Exception as e:
            logger.warning(f"Initial sync for Instagram account {ig_account.id} failed: {e}")

    # Invalidate session token after successful connection so it cannot be reused
    await _delete_oauth_session(body.session_token)

    msg = f"Successfully connected Facebook Page '{fb_account.account_name}'"
    if ig_account:
        msg += f" and Instagram account '@{ig_account.account_name}'"

    return FacebookConnectPageResponse(
        status="success",
        facebook_account=SocialAccountResponse.from_orm_model(fb_account),
        instagram_account=SocialAccountResponse.from_orm_model(ig_account) if ig_account else None,
        message=msg
    )


@router.get("/{provider}/callback", summary="Handle OAuth authorization code callback")
async def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    provider_clean = provider.lower()
    frontend_base = settings.FRONTEND_URL.rstrip('/')

    # Handle provider denial or error
    if error or error_description:
        raw_err = error_description or error or "OAuth authorization denied by user."
        if "permission" in raw_err.lower() or "scope" in raw_err.lower():
            friendly_msg = "Meta rejected one or more requested permissions. Please verify that required permissions are added to your Meta App and that your Facebook account is added under App Roles in the Meta Developer Console."
        elif "denied" in raw_err.lower() or "cancel" in raw_err.lower():
            friendly_msg = "OAuth connection was cancelled or denied by user."
        else:
            friendly_msg = f"OAuth error: {raw_err}"
        msg = urllib.parse.quote(friendly_msg)
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={provider_clean}&provider={provider_clean}&message={msg}",
            status_code=307
        )

    if not code or not state:
        msg = urllib.parse.quote("Missing required authorization code or state parameter.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={provider_clean}&provider={provider_clean}&message={msg}",
            status_code=307
        )

    # Validate state parameter
    state_payload = await _retrieve_and_delete_oauth_state(state)
    if not state_payload:
        msg = urllib.parse.quote("Invalid or expired OAuth state session. Please try connecting again.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={provider_clean}&provider={provider_clean}&message={msg}",
            status_code=307
        )

    user_id = state_payload.get("user_id")
    team_id = state_payload.get("team_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        msg = urllib.parse.quote("Authenticated user session not found.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={provider_clean}&provider={provider_clean}&message={msg}",
            status_code=307
        )

    platform_enum = PROVIDER_KEY_MAP.get(provider_clean, SocialPlatform.FACEBOOK)
    adapter = get_platform_adapter(platform_enum)
    redirect_uri = _get_provider_redirect_uri(provider_clean)

    try:
        token_data = adapter.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        if not access_token:
            raise ValueError("Token endpoint did not return an access token.")

        # Facebook/Instagram flow: Fetch Facebook Pages managed by user
        # NOTE: Instagram is connected via a linked Facebook Page (instagram_business_account field).
        # When provider=instagram, OAuth redirects to /facebook/callback (shared redirect URI),
        # so provider_clean='facebook' here. Use state_payload["provider"] to recover the original intent.
        original_provider = state_payload.get("provider", provider_clean)
        if provider_clean in ("facebook", "instagram") or original_provider in ("facebook", "instagram"):
            pages = []
            fb_adapter = get_platform_adapter(SocialPlatform.FACEBOOK)
            if hasattr(fb_adapter, "get_user_pages"):
                try:
                    pages = fb_adapter.get_user_pages(access_token)
                except Exception as e:
                    logger.warning(f"Error fetching Facebook pages for {original_provider} flow: {e}")
                    pages = []

            if pages:
                session_token = secrets.token_urlsafe(32)
                now = datetime.now(timezone.utc)
                session_payload = {
                    "session_token": session_token,
                    "user_id": user_id,
                    "team_id": team_id,
                    "provider": "facebook",
                    "preferred_platform": original_provider,  # hint for UI: 'instagram' or 'facebook'
                    "user_access_token": access_token,
                    "pages": pages,
                    "created_at": now.isoformat(),
                    "expires_at": (now + timedelta(seconds=600)).isoformat()
                }
                await _save_oauth_session(session_token, session_payload)

                # Pass the original provider so frontend can pre-select Instagram toggle
                return RedirectResponse(
                    url=f"{frontend_base}/dashboard/accounts?status=select_pages&session_token={session_token}&platform={original_provider}&provider={original_provider}",
                    status_code=307
                )
            else:
                if original_provider == "instagram":
                    msg = urllib.parse.quote(
                        "No Facebook Pages found linked to your account. "
                        "To connect Instagram, you must manage at least one Facebook Page "
                        "that has an Instagram Professional/Business account linked to it. "
                        "Please create a Facebook Page and connect your Instagram Professional account to it first."
                    )
                else:
                    msg = urllib.parse.quote(
                        "No Facebook Pages found. You must be an admin of at least one Facebook Page to connect."
                    )
                return RedirectResponse(
                    url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={original_provider}&provider={original_provider}&message={msg}",
                    status_code=307
                )

        # Other platforms (LinkedIn, X, YouTube, Pinterest)
        profile = adapter.get_user_profile(access_token)
        expires_at = None
        if expires_in:
            expires_at = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + int(expires_in),
                tz=timezone.utc
            )

        account_in = SocialAccountCreate(
            platform=platform_enum,
            account_identifier=profile.get("account_identifier", f"{provider_clean}_{user_id}"),
            account_name=profile.get("account_name", f"{provider_clean.capitalize()} Account"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            team_id=team_id
        )

        account = social_account_service.connect_account(db, user, account_in)
        acc_name = urllib.parse.quote(account.account_name)
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=success&status=success&platform={provider_clean}&provider={provider_clean}&account_name={acc_name}&account_id={account.id}",
            status_code=307
        )

    except Exception as e:
        logger.error(f"OAuth code exchange failed for {provider_clean}: {e}", exc_info=True)
        msg = urllib.parse.quote(f"Failed to complete OAuth token exchange: {str(e)}")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?oauth=error&status=error&platform={provider_clean}&provider={provider_clean}&message={msg}",
            status_code=307
        )
