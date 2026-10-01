import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status

from app.models.social_account import SocialAccount
from app.models.user import User
from app.models.team_member import TeamMember
from app.models.team import Team
from app.models.enums import SocialPlatform, SocialAccountStatus, UserRole
from app.schemas.social_account import SocialAccountCreate, SocialAccountUpdatePermissions
from app.core.security import encrypt_token, decrypt_token
from app.integrations import get_platform_adapter

logger = logging.getLogger(__name__)


def _get_default_platform_permissions(platform: SocialPlatform) -> Dict[str, bool]:
    """Default permissions dictionary tailored per platform (Implementation Decision)."""
    defaults = {
        SocialPlatform.FACEBOOK: {"publish_posts": True, "read_insights": True, "manage_pages": True},
        SocialPlatform.INSTAGRAM: {"publish_photos": True, "publish_reels": True, "read_analytics": True},
        SocialPlatform.LINKEDIN: {"share_posts": True, "read_profile": True, "company_analytics": True},
        SocialPlatform.TWITTER: {"post_tweets": True, "read_tweets": True, "user_analytics": True},
        SocialPlatform.YOUTUBE: {"upload_videos": True, "read_channel": True, "video_analytics": True},
        SocialPlatform.PINTEREST: {"create_pins": True, "read_boards": True, "pin_analytics": True},
    }
    return defaults.get(platform, {"publish": True, "read": True})


def _verify_account_access(db: Session, user: User, account: SocialAccount) -> bool:
    """Check if the user is the owner or a member of the team managing the account."""
    if user.role == UserRole.ADMINISTRATOR:
        return True
    if account.user_id == user.id:
        return True
    if account.team_id:
        membership = db.query(TeamMember).filter_by(team_id=account.team_id, user_id=user.id).first()
        if membership:
            return True
        team = db.query(Team).filter_by(id=account.team_id, owner_id=user.id).first()
        if team:
            return True
    return False


def connect_account(db: Session, user: User, account_in: SocialAccountCreate) -> SocialAccount:
    """
    Connect or re-authorize a social media account.
    Enforces team authorization and prevents cross-team ownership hijacking.
    Encrypts access and refresh tokens before persisting to the database.
    """
    # 1. If team_id is provided, verify user has permission to operate on that team
    if account_in.team_id is not None:
        from app.services.team_service import TeamService
        TeamService.get_team_by_id(db, account_in.team_id, user)

    # 2. Check for cross-team conflict: is this account already actively connected to another team?
    existing_other_team = db.query(SocialAccount).filter(
        SocialAccount.platform == account_in.platform,
        SocialAccount.account_identifier == account_in.account_identifier,
        SocialAccount.connection_status != SocialAccountStatus.REVOKED
    ).first()

    if existing_other_team:
        # If connected to a different team
        if existing_other_team.team_id is not None and account_in.team_id is not None and existing_other_team.team_id != account_in.team_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This social account is already connected to another team workspace. Please disconnect it from that workspace first."
            )
        # If owned personally by another user
        if existing_other_team.user_id != user.id and existing_other_team.team_id is None and account_in.team_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This social account is already connected by another user."
            )

    # 3. Check for existing account record for this user and platform (reconnection)
    existing = db.query(SocialAccount).filter(
        SocialAccount.user_id == user.id,
        SocialAccount.platform == account_in.platform,
        SocialAccount.account_identifier == account_in.account_identifier
    ).first()

    permissions = account_in.platform_permissions or _get_default_platform_permissions(account_in.platform)
    encrypted_access = encrypt_token(account_in.access_token)
    encrypted_refresh = encrypt_token(account_in.refresh_token) if account_in.refresh_token else None

    if existing:
        # Reconnect / update existing account record
        # Security: Reconnect cannot silently transfer account ownership across teams!
        if existing.team_id is not None and account_in.team_id is not None and existing.team_id != account_in.team_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This social account is already connected to a different team workspace. Disconnect it before moving it."
            )

        existing.account_name = account_in.account_name
        existing.access_token = encrypted_access
        existing.refresh_token = encrypted_refresh
        existing.token_expires_at = account_in.token_expires_at
        existing.platform_permissions = permissions
        existing.connection_status = SocialAccountStatus.CONNECTED
        if existing.team_id is None and account_in.team_id is not None:
            existing.team_id = account_in.team_id

        db.commit()
        db.refresh(existing)
        return existing

    # 4. Create new account
    new_account = SocialAccount(
        user_id=user.id,
        team_id=account_in.team_id,
        platform=account_in.platform,
        account_identifier=account_in.account_identifier,
        account_name=account_in.account_name,
        access_token=encrypted_access,
        refresh_token=encrypted_refresh,
        token_expires_at=account_in.token_expires_at,
        platform_permissions=permissions,
        connection_status=SocialAccountStatus.CONNECTED
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


def list_accounts(
    db: Session,
    user: User,
    platform: Optional[SocialPlatform] = None,
    connection_status: Optional[SocialAccountStatus] = None,
    team_id: Optional[int] = None
) -> List[SocialAccount]:
    """Retrieve social media accounts accessible to the current user with optional filtering."""
    # Find all team IDs user is a member of
    user_team_ids = [tm.team_id for tm in db.query(TeamMember.team_id).filter_by(user_id=user.id).all()]

    if team_id is not None:
        # Enforce membership check
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        is_team_owner = team.owner_id == user.id
        is_member = team_id in user_team_ids
        is_sysadmin = user.role == UserRole.ADMINISTRATOR
        
        if not (is_team_owner or is_member or is_sysadmin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this team's accounts"
            )
        
        query = db.query(SocialAccount).filter(SocialAccount.team_id == team_id)
    else:
        query = db.query(SocialAccount).filter(
            or_(
                SocialAccount.user_id == user.id,
                SocialAccount.team_id.in_(user_team_ids) if user_team_ids else False
            )
        )

    if platform:
        query = query.filter(SocialAccount.platform == platform)
    if connection_status:
        query = query.filter(SocialAccount.connection_status == connection_status)

    return query.order_by(SocialAccount.created_at.desc()).all()


def get_account(db: Session, user: User, account_id: int) -> SocialAccount:
    """Retrieve a single social media account verifying authorization."""
    account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
    if not account or not _verify_account_access(db, user, account):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found or access unauthorized."
        )
    return account


def disconnect_account(db: Session, user: User, account_id: int) -> SocialAccount:
    """Safely disconnect/revoke a social media account and invalidate credentials on remote platform where supported."""
    account = get_account(db, user, account_id)
    account.connection_status = SocialAccountStatus.REVOKED
    try:
        if account.access_token:
            decrypted_token = decrypt_token(account.access_token)
            adapter = get_platform_adapter(account.platform)
            adapter.revoke_access(decrypted_token)
    except Exception as e:
        logger.warning(f"Could not revoke access on remote platform for account {account_id}: {e}")

    db.commit()
    db.refresh(account)
    return account


def update_account_permissions(
    db: Session,
    user: User,
    account_id: int,
    perms_in: SocialAccountUpdatePermissions
) -> SocialAccount:
    """Update platform permissions for a connected account."""
    account = get_account(db, user, account_id)
    account.platform_permissions = perms_in.platform_permissions
    db.commit()
    db.refresh(account)
    return account


def synchronize_account(db: Session, user: User, account_id: int) -> Dict[str, Any]:
    """Trigger account synchronization workflow through the integration adapter."""
    account = get_account(db, user, account_id)
    adapter = get_platform_adapter(account.platform)

    decrypted_token = decrypt_token(account.access_token)
    sync_result = adapter.synchronize_account_data(decrypted_token, account.account_identifier)

    # Update synchronization timestamp
    now = datetime.now(timezone.utc)
    account.last_synced_at = now

    # Check if remote reported expired token, revoked access, or invalid session
    if sync_result.get("is_revoked") or "revoked" in sync_result.get("message", "").lower():
        account.connection_status = SocialAccountStatus.REVOKED
    elif sync_result.get("is_token_expired") or "expired" in sync_result.get("message", "").lower():
        account.connection_status = SocialAccountStatus.EXPIRED
    elif sync_result.get("status") == "synchronized":
        account.connection_status = SocialAccountStatus.CONNECTED
        current_perms = dict(account.platform_permissions or {})
        if sync_result.get("avatar_url"):
            current_perms["avatar_url"] = sync_result["avatar_url"]
            current_perms["picture_url"] = sync_result["avatar_url"]
        if sync_result.get("username"):
            current_perms["username"] = sync_result["username"]
        if sync_result.get("biography"):
            current_perms["biography"] = sync_result["biography"]
        if sync_result.get("category"):
            current_perms["category"] = sync_result["category"]

        follower_count = sync_result.get("follower_count")
        if follower_count is not None:
            current_perms["follower_count"] = int(follower_count)
        following_count = sync_result.get("following_count")
        if following_count is not None:
            current_perms["following_count"] = int(following_count)
        post_count = sync_result.get("post_count")
        if post_count is not None:
            current_perms["post_count"] = int(post_count)

        if sync_result.get("account_name"):
            account.account_name = sync_result["account_name"]

        # Fetch recent posts / media from platform
        try:
            recent_posts = adapter.fetch_recent_posts(decrypted_token, account.account_identifier, limit=50)
            if recent_posts:
                current_perms["recent_posts"] = recent_posts[:25]
                if not current_perms.get("post_count"):
                    current_perms["post_count"] = len(recent_posts)
        except Exception as p_err:
            logger.warning(f"Recent posts fetch failed for account {account.id}: {p_err}")

        # Maintain historical daily snapshots
        today_str = now.strftime("%Y-%m-%d")
        snapshots = list(current_perms.get("snapshots") or [])
        prev_snapshot = snapshots[-1] if snapshots else None
        prev_followers = prev_snapshot.get("follower_count", current_perms.get("follower_count", 0)) if prev_snapshot else current_perms.get("follower_count", 0)
        curr_followers = current_perms.get("follower_count", 0)
        net_growth = curr_followers - prev_followers
        growth_rate = round((net_growth / max(1, prev_followers) * 100), 2) if prev_followers > 0 else 0.0

        new_snapshot = {
            "date": today_str,
            "recorded_at": now.isoformat(),
            "follower_count": curr_followers,
            "following_count": current_perms.get("following_count", 0),
            "post_count": current_perms.get("post_count", 0),
            "net_follower_growth": net_growth,
            "growth_rate": growth_rate,
        }

        # Deduplicate today's snapshot
        updated_snapshots = [s for s in snapshots if s.get("date") != today_str]
        updated_snapshots.append(new_snapshot)
        current_perms["snapshots"] = updated_snapshots[-90:]

        account.platform_permissions = current_perms

    db.commit()
    db.refresh(account)

    # Ingest into MongoDB asynchronously if active
    try:
        from app.db.mongo import get_mongo_db
        import asyncio
        m_db = get_mongo_db()
        if m_db is not None:
            from app.services.analytics_ingestion_service import AnalyticsIngestionService
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(AnalyticsIngestionService.sync_account_analytics(db, m_db, account))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(AnalyticsIngestionService.sync_account_analytics(db, m_db, account))
                loop.close()
    except Exception as m_err:
        logger.warning(f"Async Mongo analytics ingestion deferred for account {account.id}: {m_err}")

    return {
        "account_id": account.id,
        "platform": account.platform,
        "synced_at": now,
        "connection_status": account.connection_status,
        "sync_status": "success",
        "message": f"Synchronization workflow executed for {account.platform.value} account '{account.account_name}'.",
        "details": sync_result
    }


def check_token_status(account: SocialAccount) -> Dict[str, Any]:
    """Determine token validity without external API calls based on stored metadata."""
    is_expired = False
    if account.token_expires_at:
        is_expired = account.token_expires_at <= datetime.now(timezone.utc)

    return {
        "id": account.id,
        "platform": account.platform,
        "account_name": account.account_name,
        "connection_status": account.connection_status,
        "is_token_expired": is_expired,
        "token_expires_at": account.token_expires_at,
        "last_synced_at": account.last_synced_at
    }
