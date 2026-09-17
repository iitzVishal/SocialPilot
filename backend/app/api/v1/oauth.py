import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.enums import SocialPlatform
from app.schemas.social_account import SocialAccountCreate
from app.services import social_account_service
from app.integrations import get_platform_adapter
from app.core.config import settings
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory fallback state storage for environments without Redis
_IN_MEMORY_STATE_CACHE: Dict[str, Dict[str, Any]] = {}

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
        return settings.INSTAGRAM_REDIRECT_URI
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
    # Save in Redis with 10-min TTL
    try:
        redis = get_redis_client()
        if redis is not None:
            await redis.set(f"oauth_state:{state}", json.dumps(payload), ex=600)
    except Exception as e:
        logger.warning(f"Redis state save fallback to memory: {e}")

    # Always mirror to in-memory fallback
    _IN_MEMORY_STATE_CACHE[state] = payload


async def _retrieve_and_delete_oauth_state(state: str) -> Optional[Dict[str, Any]]:
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

    if not payload and state in _IN_MEMORY_STATE_CACHE:
        payload = _IN_MEMORY_STATE_CACHE.pop(state)

    return payload


@router.get("/{provider}/authorize", summary="Generate platform OAuth authorization URL")
async def authorize_oauth(
    provider: str,
    team_id: Optional[int] = Query(None, description="Optional target team workspace ID"),
    redirect: bool = Query(False, description="If True, issues HTTP 307 redirect directly to provider"),
    current_user: User = Depends(get_current_active_user)
):
    provider_clean = provider.lower()
    if provider_clean not in PROVIDER_KEY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: '{provider}'. Supported: instagram, facebook, linkedin, x, youtube, pinterest."
        )

    # Check provider credentials configured
    _verify_provider_configured(provider_clean)

    # Generate secure random state token
    state_token = secrets.token_urlsafe(32)
    state_payload = {
        "user_id": current_user.id,
        "team_id": team_id,
        "provider": provider_clean,
        "created_at": datetime.now(timezone.utc).isoformat()
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
        msg = urllib.parse.quote(error_description or error or "OAuth authorization denied by user.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?status=error&provider={provider_clean}&message={msg}",
            status_code=307
        )

    if not code or not state:
        msg = urllib.parse.quote("Missing required authorization code or state parameter.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?status=error&provider={provider_clean}&message={msg}",
            status_code=307
        )

    # Validate state parameter
    state_payload = await _retrieve_and_delete_oauth_state(state)
    if not state_payload:
        msg = urllib.parse.quote("Invalid or expired OAuth state session. Please try connecting again.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?status=error&provider={provider_clean}&message={msg}",
            status_code=307
        )

    user_id = state_payload.get("user_id")
    team_id = state_payload.get("team_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        msg = urllib.parse.quote("Authenticated user session not found.")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?status=error&provider={provider_clean}&message={msg}",
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

        # Retrieve profile metadata
        profile = adapter.get_user_profile(access_token)

        # Calculate token expiration timestamp
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
            url=f"{frontend_base}/dashboard/accounts?status=success&platform={provider_clean}&account_name={acc_name}",
            status_code=307
        )

    except Exception as e:
        logger.error(f"OAuth code exchange failed for {provider_clean}: {e}", exc_info=True)
        msg = urllib.parse.quote(f"Failed to complete OAuth token exchange: {str(e)}")
        return RedirectResponse(
            url=f"{frontend_base}/dashboard/accounts?status=error&provider={provider_clean}&message={msg}",
            status_code=307
        )
