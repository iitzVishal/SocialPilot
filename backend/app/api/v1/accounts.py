import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.enums import SocialPlatform, SocialAccountStatus
from app.schemas.social_account import (
    SocialAccountCreate,
    SocialAccountResponse,
    SocialAccountStatusResponse,
    SocialAccountUpdatePermissions,
    SocialAccountSyncResponse
)
from app.services import social_account_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED, summary="Connect social media account")
def connect_account(
    account_in: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Connect a social media account.
    Access and refresh tokens are securely encrypted before persistence.
    Raw tokens are never returned in the API response.
    """
    account = social_account_service.connect_account(db, current_user, account_in)
    return SocialAccountResponse.from_orm_model(account)


@router.get("", response_model=List[SocialAccountResponse], summary="List connected social media accounts")
def list_accounts(
    platform: Optional[SocialPlatform] = Query(None, description="Filter by social media platform"),
    connection_status: Optional[SocialAccountStatus] = Query(None, description="Filter by account status"),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve social media accounts accessible to the authenticated user with optional platform/status filters."""
    accounts = social_account_service.list_accounts(db, current_user, platform=platform, connection_status=connection_status, team_id=team_id)
    return [SocialAccountResponse.from_orm_model(acc) for acc in accounts]


@router.get("/{account_id}", response_model=SocialAccountResponse, summary="Get single social media account")
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve safe social account details verifying ownership/authorization."""
    account = social_account_service.get_account(db, current_user, account_id)
    return SocialAccountResponse.from_orm_model(account)


@router.delete("/{account_id}", response_model=SocialAccountResponse, summary="Disconnect social media account")
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Safely disconnect/revoke a social media account connection."""
    account = social_account_service.disconnect_account(db, current_user, account_id)
    return SocialAccountResponse.from_orm_model(account)


@router.get("/{account_id}/status", response_model=SocialAccountStatusResponse, summary="Check social account connection & token status")
def get_account_status(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check account connection status and token validity without third-party network overhead."""
    account = social_account_service.get_account(db, current_user, account_id)
    status_data = social_account_service.check_token_status(account)
    return SocialAccountStatusResponse(**status_data)


@router.patch("/{account_id}/permissions", response_model=SocialAccountResponse, summary="Update account platform permissions")
def update_permissions(
    account_id: int,
    perms_in: SocialAccountUpdatePermissions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update platform permissions for a connected social account."""
    account = social_account_service.update_account_permissions(db, current_user, account_id, perms_in)
    return SocialAccountResponse.from_orm_model(account)


@router.post("/{account_id}/sync", response_model=SocialAccountSyncResponse, summary="Trigger account synchronization")
def sync_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger the account synchronization workflow."""
    result = social_account_service.synchronize_account(db, current_user, account_id)
    return SocialAccountSyncResponse(
        account_id=result["account_id"],
        platform=result["platform"],
        synced_at=result["synced_at"],
        connection_status=result["connection_status"],
        sync_status=result["sync_status"],
        message=result["message"]
    )


@router.get("/{account_id}/instagram/snapshots", summary="Get historical Instagram daily metric snapshots")
def get_instagram_snapshots(
    account_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days of historical snapshots"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve stored PostgreSQL historical snapshots for follower growth, reach, and impressions.
    Enforces user authorization and team isolation.
    """
    account = social_account_service.get_account(db, current_user, account_id)
    if account.platform != SocialPlatform.INSTAGRAM:
        return []
    from app.services.instagram_command_service import InstagramCommandService
    snapshots = InstagramCommandService.get_historical_snapshots(db, account_id, days=days)
    return [
        {
            "id": s.id,
            "account_id": s.account_id,
            "date": s.date.isoformat(),
            "follower_count": s.follower_count,
            "following_count": s.following_count,
            "media_count": s.media_count,
            "net_follower_growth": s.net_follower_growth,
            "growth_rate": s.growth_rate,
            "impressions": s.impressions,
            "reach": s.reach,
            "profile_views": s.profile_views,
            "website_clicks": s.website_clicks,
            "recorded_at": s.recorded_at.isoformat() if s.recorded_at else None
        }
        for s in snapshots
    ]


@router.get("/{account_id}/instagram/media", summary="Get synchronized Instagram media and reels")
def get_instagram_media(
    account_id: int,
    media_type: Optional[str] = Query(None, description="Filter by IMAGE, VIDEO, REELS, CAROUSEL"),
    sort_by: str = Query("performance_score", description="Sort by: performance_score, engagement, likes, comments, recent"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve synchronized Instagram media with real engagement metrics and performance scores."""
    account = social_account_service.get_account(db, current_user, account_id)
    if account.platform != SocialPlatform.INSTAGRAM:
        return []
    from app.services.instagram_command_service import InstagramCommandService
    media_items = InstagramCommandService.get_top_media(db, account_id, media_type=media_type, sort_by=sort_by, limit=limit)
    return [
        {
            "id": m.id,
            "account_id": m.account_id,
            "external_media_id": m.external_media_id,
            "caption": m.caption,
            "media_type": m.media_type,
            "permalink": m.permalink,
            "thumbnail_url": m.thumbnail_url or m.media_url,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "like_count": m.like_count,
            "comments_count": m.comments_count,
            "views_count": m.views_count,
            "reach_count": m.reach_count,
            "shares_count": m.shares_count,
            "saved_count": m.saved_count,
            "engagement": m.engagement,
            "performance_score": m.performance_score,
            "raw_insights": m.raw_insights or {}
        }
        for m in media_items
    ]


@router.get("/{account_id}/instagram/performance-score", summary="Get SocialPilot Performance Score")
def get_instagram_performance_score(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the deterministic SocialPilot Performance Score computed from real synchronized data."""
    account = social_account_service.get_account(db, current_user, account_id)
    from app.services.instagram_command_service import InstagramCommandService
    return InstagramCommandService.compute_account_performance_score(db, account_id)


@router.get("/{account_id}/instagram/media/{media_id}/comments", summary="Get comments for an Instagram post")
def get_instagram_post_comments(
    account_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Fetch comments for an Instagram post from PostgreSQL / live Meta API where permitted."""
    account = social_account_service.get_account(db, current_user, account_id)
    from app.models.instagram_data import InstagramMedia, InstagramComment
    media = db.query(InstagramMedia).filter(InstagramMedia.id == media_id, InstagramMedia.account_id == account.id).first()
    if not media:
        return []

    # Check cached comments in database first
    comments = db.query(InstagramComment).filter(InstagramComment.media_id == media.id).order_by(InstagramComment.created_at.desc()).all()
    if not comments:
        # Fetch live comments from Graph API and persist
        try:
            from app.core.security import decrypt_token
            from app.integrations import get_platform_adapter
            adapter = get_platform_adapter(SocialPlatform.INSTAGRAM)
            token = decrypt_token(account.access_token) if account.access_token else ""
            raw_comments = adapter.fetch_media_comments(token, media.external_media_id, limit=25)
            for c in raw_comments:
                cid = c.get("external_comment_id")
                if not cid:
                    continue
                existing_c = db.query(InstagramComment).filter(InstagramComment.external_comment_id == cid).first()
                if not existing_c:
                    parsed_c_ts = None
                    if c.get("timestamp"):
                        try:
                            parsed_c_ts = datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00"))
                        except Exception:
                            pass
                    new_c = InstagramComment(
                        media_id=media.id,
                        external_comment_id=cid,
                        from_username=c.get("username"),
                        text=c.get("text", ""),
                        timestamp=parsed_c_ts,
                        like_count=c.get("like_count", 0)
                    )
                    db.add(new_c)
            db.commit()
            comments = db.query(InstagramComment).filter(InstagramComment.media_id == media.id).all()
        except Exception as err:
            logger.warning(f"Live comments fetch failed: {err}")

    return [
        {
            "id": c.id,
            "media_id": c.media_id,
            "external_comment_id": c.external_comment_id,
            "from_username": c.from_username,
            "text": c.text,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "like_count": c.like_count,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in comments
    ]


@router.post("/{account_id}/instagram/media/{media_id}/comments", summary="Post a comment or reply")
def post_instagram_comment(
    account_id: int,
    media_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Post comment/reply to an Instagram media post via Meta Graph API."""
    account = social_account_service.get_account(db, current_user, account_id)
    msg = body.get("message")
    if not msg:
        raise HTTPException(status_code=400, detail="Comment message is required.")

    from app.models.instagram_data import InstagramMedia, InstagramComment
    media = db.query(InstagramMedia).filter(InstagramMedia.id == media_id, InstagramMedia.account_id == account.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")

    from app.core.security import decrypt_token
    from app.integrations import get_platform_adapter
    adapter = get_platform_adapter(SocialPlatform.INSTAGRAM)
    token = decrypt_token(account.access_token) if account.access_token else ""

    res = adapter.reply_to_comment(token, media.external_media_id, msg)
    ext_id = res.get("id", f"c_{secrets.token_hex(6)}")

    new_c = InstagramComment(
        media_id=media.id,
        external_comment_id=ext_id,
        from_username=account.account_name,
        text=msg,
        timestamp=datetime.now(timezone.utc),
        like_count=0
    )
    db.add(new_c)
    db.commit()
    db.refresh(new_c)
    return {
        "id": new_c.id,
        "external_comment_id": ext_id,
        "text": msg,
        "status": "published"
    }


@router.get("/{account_id}/instagram/messages", summary="Check Instagram direct messaging capabilities")
def get_instagram_messages_status(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Check Instagram Messaging API support.
    Accurately represents Meta API permissions without fake data.
    """
    account = social_account_service.get_account(db, current_user, account_id)
    perms = account.platform_permissions or {}
    has_msg_scope = "instagram_manage_messages" in (perms.get("scopes") or [])

    return {
        "supported": False,
        "has_permission": has_msg_scope,
        "status": "PERMISSION_REQUIRED",
        "notice": "Instagram Direct Messaging requires Meta App Review for the 'instagram_manage_messages' permission and Advanced Access in Meta Developer Console.",
        "documentation_url": "https://developers.facebook.com/docs/messenger-platform/instagram"
    }

