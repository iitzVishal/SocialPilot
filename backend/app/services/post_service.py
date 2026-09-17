import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.campaign import Campaign
from app.models.enums import SocialPlatform, PostStatus, PublishResultStatus, SocialAccountStatus, UserRole, NotificationType
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    AccountPublishResult,
)
from app.services.notification_service import NotificationService
from app.db.mongo import ensure_active_mongo_db


logger = logging.getLogger(__name__)

# Authoritative State Machine Transitions
VALID_TRANSITIONS: Dict[PostStatus, List[PostStatus]] = {
    PostStatus.DRAFT: [PostStatus.SCHEDULED, PostStatus.QUEUED, PostStatus.PENDING_APPROVAL],
    PostStatus.PENDING_APPROVAL: [PostStatus.APPROVED, PostStatus.REJECTED, PostStatus.DRAFT],
    PostStatus.APPROVED: [PostStatus.SCHEDULED, PostStatus.QUEUED, PostStatus.DRAFT],
    PostStatus.REJECTED: [PostStatus.DRAFT, PostStatus.PENDING_APPROVAL],
    PostStatus.SCHEDULED: [PostStatus.QUEUED, PostStatus.DRAFT, PostStatus.CANCELLED],
    PostStatus.QUEUED: [PostStatus.PUBLISHING, PostStatus.CANCELLED],
    PostStatus.PUBLISHING: [PostStatus.PUBLISHED, PostStatus.PARTIALLY_PUBLISHED, PostStatus.FAILED],
    PostStatus.PARTIALLY_PUBLISHED: [PostStatus.QUEUED, PostStatus.DRAFT],
    PostStatus.FAILED: [PostStatus.QUEUED, PostStatus.DRAFT],
    PostStatus.CANCELLED: [PostStatus.DRAFT, PostStatus.SCHEDULED],
    PostStatus.PUBLISHED: [],  # Terminal state
}


async def ensure_post_indexes(mongo_db: AsyncIOMotorDatabase) -> None:
    """Create MongoDB indexes for the posts collection idempotently."""
    try:
        posts = mongo_db["posts"]
        # Index 1: User & status query index with creation order
        await posts.create_index([("user_id", 1), ("status", 1), ("created_at", -1)], name="idx_user_status_created")
        # Index 2: Scheduler query index
        await posts.create_index([("status", 1), ("scheduled_at", 1)], name="idx_status_scheduled")
        # Index 3: Target accounts lookup index
        await posts.create_index([("target_accounts", 1)], name="idx_target_accounts")
        logger.info("MongoDB posts collection indexes verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not create MongoDB indexes for posts: {e}")


def _serialize_mongo_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB document to JSON-compatible dict with string ID and proper field mapping."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def verify_target_accounts(
    db: Session,
    user: User,
    target_accounts: List[int],
    target_platforms: List[SocialPlatform],
    team_id: Optional[int] = None
) -> List[SocialAccount]:
    """
    Validate that all target social accounts exist in PostgreSQL, belong to the user/team,
    are in connected state, and match target platforms.
    """
    if not target_accounts:
        return []

    # Query accounts from PostgreSQL
    accounts = db.query(SocialAccount).filter(SocialAccount.id.in_(target_accounts)).all()
    found_ids = {a.id for a in accounts}

    missing_ids = set(target_accounts) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target social accounts not found: {list(missing_ids)}"
        )

    # Verify team access if team_id is provided
    if team_id:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found"
            )
        is_team_owner = team.owner_id == user.id
        membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        if not (is_team_owner or membership or user.role.value == "administrator"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User is not a member or owner of team {team_id}"
            )

    platform_set = {p.value if hasattr(p, "value") else str(p) for p in target_platforms}

    for account in accounts:
        # Ownership check
        is_owner = account.user_id == user.id
        is_team_account = team_id and account.team_id == team_id
        if not (is_owner or is_team_account or user.role.value == "administrator"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to social account {account.id} ({account.account_name})"
            )

        # Connection health check
        if account.connection_status != SocialAccountStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Social account {account.id} ({account.account_name}) is {account.connection_status.value}. Reconnection required."
            )

        # Platform compatibility check
        account_platform = account.platform.value if hasattr(account.platform, "value") else str(account.platform)
        if platform_set and account_platform not in platform_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {account.id} platform ({account_platform}) is not in target platforms list ({list(platform_set)})"
            )

    return accounts


def verify_campaign_access(
    db: Session,
    campaign_id: Optional[int],
    team_id: Optional[int]
) -> Optional[Campaign]:
    """Validate that campaign exists in PostgreSQL and belongs to the target team workspace."""
    if not campaign_id:
        return None
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found"
        )
    if team_id and campaign.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campaign {campaign_id} does not belong to team {team_id}"
        )
    return campaign


class PostService:
    @staticmethod
    async def create_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_in: PostCreate
    ) -> Dict[str, Any]:
        # Verify target accounts if provided
        if post_in.target_accounts:
            verify_target_accounts(
                db=db,
                user=user,
                target_accounts=post_in.target_accounts,
                target_platforms=post_in.target_platforms,
                team_id=post_in.team_id
            )

        # Verify campaign if provided
        if post_in.campaign_id:
            verify_campaign_access(
                db=db,
                campaign_id=post_in.campaign_id,
                team_id=post_in.team_id
            )

        # Enforce approval boundary check on direct scheduling/publishing
        if post_in.publish_now or post_in.scheduled_at is not None:
            team_id = post_in.team_id
            if team_id:
                team = db.query(Team).filter(Team.id == team_id).first()
                if team and team.require_post_approval:
                    is_owner = team.owner_id == user.id
                    is_sysadmin = user.role == UserRole.ADMINISTRATOR
                    membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
                    is_team_admin = membership and membership.role == UserRole.ADMINISTRATOR
                    
                    if not (is_owner or is_sysadmin or is_team_admin):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Post approval required. You cannot publish or schedule posts directly."
                        )

        # Determine initial status
        initial_status = PostStatus.DRAFT
        if post_in.publish_now:
            initial_status = PostStatus.QUEUED
        elif post_in.scheduled_at is not None:
            initial_status = PostStatus.SCHEDULED

        now_utc = datetime.now(timezone.utc)
        post_doc = {
            "user_id": user.id,
            "team_id": post_in.team_id,
            "campaign_id": getattr(post_in, "campaign_id", None),
            "title": post_in.title,
            "base_content": post_in.base_content,
            "media_attachments": [m.model_dump() for m in post_in.media_attachments],
            "target_platforms": [p.value if hasattr(p, "value") else str(p) for p in post_in.target_platforms],
            "target_accounts": post_in.target_accounts,
            "platform_customizations": {
                k: v.model_dump() for k, v in post_in.platform_customizations.items()
            },
            "status": initial_status.value,
            "scheduled_at": post_in.scheduled_at,
            "published_at": None,
            "celery_task_id": None,
            "publish_results": {},
            "created_at": now_utc,
            "updated_at": now_utc,
        }

        mongo_db = ensure_active_mongo_db(mongo_db)
        posts_coll = mongo_db["posts"]
        result = await posts_coll.insert_one(post_doc)
        post_doc["_id"] = result.inserted_id
        return _serialize_mongo_doc(post_doc)

    @staticmethod
    async def get_post_by_id(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Fetch a single post by MongoDB ID, enforcing user or team ownership."""
        try:
            oid = ObjectId(post_id)
        except (InvalidId, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        doc = await mongo_db["posts"].find_one({"_id": oid})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # Ownership authorization check
        is_owner = doc.get("user_id") == user.id
        is_admin = user.role.value == "administrator"
        team_id = doc.get("team_id")
        is_team_member = False
        if team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            is_team_owner = team and team.owner_id == user.id
            membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
            if is_team_owner or membership:
                is_team_member = True

        if not (is_owner or is_team_member or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this post")

        return _serialize_mongo_doc(doc)

    @staticmethod
    async def list_posts(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        team_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        status_filter: Optional[PostStatus] = None,
        platform_filter: Optional[SocialPlatform] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query posts with filters for user/team, campaign, status, platform, and date range."""
        query: Dict[str, Any] = {}

        if user.role.value == "administrator" and not team_id:
            pass  # Admin can query all posts
        elif team_id:
            # Verify team membership or ownership
            team = db.query(Team).filter(Team.id == team_id).first()
            is_team_owner = team and team.owner_id == user.id
            membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
            if not (is_team_owner or membership or user.role.value == "administrator"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to team posts")
            query["team_id"] = team_id
        else:
            query["user_id"] = user.id

        if campaign_id is not None:
            query["campaign_id"] = campaign_id

        if status_filter:
            query["status"] = status_filter.value if hasattr(status_filter, "value") else str(status_filter)

        if platform_filter:
            plat_str = platform_filter.value if hasattr(platform_filter, "value") else str(platform_filter)
            query["target_platforms"] = plat_str

        if start_date or end_date:
            date_query: Dict[str, Any] = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["created_at"] = date_query

        posts_coll = mongo_db["posts"]
        total = await posts_coll.count_documents(query)
        cursor = posts_coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        return [_serialize_mongo_doc(d) for d in docs], total

    @staticmethod
    async def update_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str,
        post_update: PostUpdate
    ) -> Dict[str, Any]:
        """
        Update an existing post draft or modify post details.
        Rejects modifications to terminal posts (PUBLISHED) or locked execution states (QUEUED, PUBLISHING).
        """
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if current_status in (PostStatus.PUBLISHED, PostStatus.PUBLISHING, PostStatus.QUEUED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit post in '{current_status.value}' state. Unschedule or cancel first."
            )

        update_data: Dict[str, Any] = {}
        if post_update.title is not None:
            update_data["title"] = post_update.title
        if post_update.base_content is not None:
            update_data["base_content"] = post_update.base_content
        if post_update.media_attachments is not None:
            update_data["media_attachments"] = [m.model_dump() for m in post_update.media_attachments]
        if post_update.target_platforms is not None:
            update_data["target_platforms"] = [p.value if hasattr(p, "value") else str(p) for p in post_update.target_platforms]
        if post_update.target_accounts is not None:
            # Verify target accounts
            platforms = post_update.target_platforms or [SocialPlatform(p) for p in current_post["target_platforms"]]
            verify_target_accounts(
                db=db,
                user=user,
                target_accounts=post_update.target_accounts,
                target_platforms=platforms,
                team_id=current_post.get("team_id")
            )
            update_data["target_accounts"] = post_update.target_accounts
        if post_update.platform_customizations is not None:
            update_data["platform_customizations"] = {
                k: v.model_dump() for k, v in post_update.platform_customizations.items()
            }
        if post_update.scheduled_at is not None:
            update_data["scheduled_at"] = post_update.scheduled_at
        if post_update.campaign_id is not None:
            verify_campaign_access(
                db=db,
                campaign_id=post_update.campaign_id,
                team_id=current_post.get("team_id")
            )
            update_data["campaign_id"] = post_update.campaign_id

        # Revert back to DRAFT if post is currently approved, pending approval, or rejected
        if current_status in (PostStatus.APPROVED, PostStatus.PENDING_APPROVAL, PostStatus.REJECTED):
            update_data["status"] = PostStatus.DRAFT.value
            update_data["approved_by"] = None
            update_data["approved_at"] = None
            update_data["rejection_reason"] = None
            update_data["rejected_by"] = None
            update_data["rejected_at"] = None

        update_data["updated_at"] = datetime.now(timezone.utc)

        posts_coll = mongo_db["posts"]
        await posts_coll.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_data}
        )

        return await PostService.get_post_by_id(mongo_db, db, user, post_id)

    @staticmethod
    async def delete_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> bool:
        """
        Delete a post document.
        DRAFT: hard delete allowed.
        SCHEDULED / QUEUED: requires cancellation/unscheduling first.
        """
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if current_status != PostStatus.DRAFT and current_status != PostStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot hard-delete post in '{current_status.value}' state. Only DRAFT or CANCELLED posts can be deleted."
            )

        result = await mongo_db["posts"].delete_one({"_id": ObjectId(post_id)})
        return result.deleted_count > 0

    @staticmethod
    async def schedule_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str,
        scheduled_at: datetime
    ) -> Dict[str, Any]:
        """Assign schedule timestamp and transition post state to SCHEDULED."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        # Enforce approval boundary check on scheduling
        team_id = current_post.get("team_id")
        if team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team and team.require_post_approval:
                is_owner = team.owner_id == user.id
                is_sysadmin = user.role == UserRole.ADMINISTRATOR
                membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
                is_team_admin = membership and membership.role == UserRole.ADMINISTRATOR
                
                if not (is_owner or is_sysadmin or is_team_admin):
                    # Normal members require approved status
                    if current_status != PostStatus.APPROVED:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Post approval required. Post must be approved before scheduling."
                        )

        # Validate state transition
        if PostStatus.SCHEDULED not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition: cannot schedule post from '{current_status.value}' state."
            )

        # Precondition check: must have target accounts
        if not current_post.get("target_accounts"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule post without selected target accounts."
            )

        now_utc = datetime.now(timezone.utc)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at <= now_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled timestamp must be in the future (UTC)."
            )

        # Atomic transition
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.SCHEDULED.value,
                    "scheduled_at": scheduled_at,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Post status was modified concurrently. Please refresh and try again."
            )

        return _serialize_mongo_doc(res)

    @staticmethod
    async def unschedule_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Revert a SCHEDULED post back to DRAFT."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if current_status != PostStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot unschedule post from '{current_status.value}' state. Post is not currently scheduled."
            )

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": PostStatus.SCHEDULED.value},
            {
                "$set": {
                    "status": PostStatus.DRAFT.value,
                    "scheduled_at": None,
                    "celery_task_id": None,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent post update conflict")

        return _serialize_mongo_doc(res)

    @staticmethod
    async def cancel_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Cancel a SCHEDULED or QUEUED post."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if PostStatus.CANCELLED not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel post in '{current_status.value}' state."
            )

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.CANCELLED.value,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent post update conflict")

        return _serialize_mongo_doc(res)

    @staticmethod
    async def queue_post_for_publish(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Queue a DRAFT, SCHEDULED, or FAILED post for immediate background dispatch."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        # Enforce approval boundary check on publishing
        team_id = current_post.get("team_id")
        if team_id:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team and team.require_post_approval:
                is_owner = team.owner_id == user.id
                is_sysadmin = user.role == UserRole.ADMINISTRATOR
                membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
                is_team_admin = membership and membership.role == UserRole.ADMINISTRATOR
                
                if not (is_owner or is_sysadmin or is_team_admin):
                    # Normal members require approved status
                    if current_status != PostStatus.APPROVED:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Post approval required. Post must be approved before publishing."
                        )

        if PostStatus.QUEUED not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot queue post from '{current_status.value}' state."
            )

        if not current_post.get("target_accounts"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish post without selected target accounts."
            )

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.QUEUED.value,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent state change conflict")

        return _serialize_mongo_doc(res)

    @staticmethod
    async def atomic_claim_for_publishing(
        mongo_db: AsyncIOMotorDatabase,
        post_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Atomic worker claim operation transitioning QUEUED -> PUBLISHING.
        Prevents two workers or tasks from executing the same post dispatch concurrently.
        """
        try:
            oid = ObjectId(post_id)
        except (InvalidId, TypeError):
            return None

        now_utc = datetime.now(timezone.utc)
        claimed = await mongo_db["posts"].find_one_and_update(
            {"_id": oid, "status": PostStatus.QUEUED.value},
            {
                "$set": {
                    "status": PostStatus.PUBLISHING.value,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        return _serialize_mongo_doc(claimed)

    @staticmethod
    async def record_publish_results(
        mongo_db: AsyncIOMotorDatabase,
        post_id: str,
        new_results: Dict[str, AccountPublishResult]
    ) -> Dict[str, Any]:
        """
        Persist execution results per social account and transition post state to
        PUBLISHED, PARTIALLY_PUBLISHED, or FAILED. Never overwrites previously successful results.
        """
        try:
            oid = ObjectId(post_id)
        except (InvalidId, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")

        current = await mongo_db["posts"].find_one({"_id": oid})
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        existing_results = current.get("publish_results", {})
        merged_results: Dict[str, Any] = dict(existing_results)

        for account_key, result in new_results.items():
            result_dict = result.model_dump() if hasattr(result, "model_dump") else dict(result)
            # If previous dispatch was already successful, preserve it
            if existing_results.get(account_key, {}).get("status") == PublishResultStatus.SUCCESS.value:
                continue
            merged_results[account_key] = result_dict

        # Evaluate overall status across all target accounts
        target_accounts = current.get("target_accounts", [])
        success_count = sum(
            1 for aid in target_accounts if merged_results.get(str(aid), {}).get("status") == PublishResultStatus.SUCCESS.value
        )
        failed_count = sum(
            1 for aid in target_accounts if merged_results.get(str(aid), {}).get("status") in (
                PublishResultStatus.FAILED.value,
                PublishResultStatus.PENDING_EXTERNAL_INTEGRATION.value,
                PublishResultStatus.UNCONFIGURED.value
            )
        )
        total_targets = len(target_accounts)

        if success_count == total_targets and total_targets > 0:
            final_status = PostStatus.PUBLISHED
        elif success_count > 0 and failed_count > 0:
            final_status = PostStatus.PARTIALLY_PUBLISHED
        else:
            final_status = PostStatus.FAILED

        now_utc = datetime.now(timezone.utc)
        update_data = {
            "publish_results": merged_results,
            "status": final_status.value,
            "published_at": now_utc if final_status == PostStatus.PUBLISHED else None,
            "updated_at": now_utc,
        }

        updated = await mongo_db["posts"].find_one_and_update(
            {"_id": oid},
            {"$set": update_data},
            return_document=True
        )

        return _serialize_mongo_doc(updated)

    @staticmethod
    async def submit_for_approval(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Transition a DRAFT or REJECTED post state to PENDING_APPROVAL."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if PostStatus.PENDING_APPROVAL not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit post for approval from state '{current_status.value}'."
            )

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.PENDING_APPROVAL.value,
                    "approval_requested_at": now_utc,
                    "approved_by": None,
                    "approved_at": None,
                    "rejected_by": None,
                    "rejected_at": None,
                    "rejection_reason": None,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent update conflict")

        # In-App Notification to team owner (fail-safe)
        try:
            team_id = current_post.get("team_id")
            if team_id:
                team = db.query(Team).filter(Team.id == team_id).first()
                if team and team.owner_id != user.id:
                    NotificationService.create_notification(
                        db=db,
                        user_id=team.owner_id,
                        team_id=team_id,
                        type=NotificationType.POST_SUBMITTED,
                        title="Post Needs Approval",
                        message=f"Post '{current_post.get('title') or 'Untitled'}' was submitted for approval.",
                        link="/dashboard/posts"
                    )
        except Exception as e:
            logger.error(f"Failed to create notification on post submission: {e}")

        return _serialize_mongo_doc(res)

    @staticmethod
    async def approve_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str
    ) -> Dict[str, Any]:
        """Approve a post (requires Team Owner, Team Admin, or System Admin privileges)."""
        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if PostStatus.APPROVED not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve post in state '{current_status.value}'."
            )

        team_id = current_post.get("team_id")
        if not team_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only workspace posts require approval.")

        team = db.query(Team).filter(Team.id == team_id).first()
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR
        membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        is_team_admin = membership and membership.role == UserRole.ADMINISTRATOR

        if not (is_owner or is_sysadmin or is_team_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to approve posts in this workspace.")

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.APPROVED.value,
                    "approved_by": user.id,
                    "approved_at": now_utc,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent update conflict")

        # In-App Notification to post author (fail-safe)
        try:
            post_author_id = current_post.get("user_id")
            if post_author_id and post_author_id != user.id:
                NotificationService.create_notification(
                    db=db,
                    user_id=post_author_id,
                    team_id=team_id,
                    type=NotificationType.POST_APPROVED,
                    title="Post Approved",
                    message=f"Your post '{current_post.get('title') or 'Untitled'}' was approved.",
                    link="/dashboard/posts"
                )
        except Exception as e:
            logger.error(f"Failed to create notification on post approval: {e}")

        return _serialize_mongo_doc(res)

    @staticmethod
    async def reject_post(
        mongo_db: AsyncIOMotorDatabase,
        db: Session,
        user: User,
        post_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Reject a post (requires Team Owner, Team Admin, or System Admin privileges)."""
        if not reason or not reason.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason is required.")

        current_post = await PostService.get_post_by_id(mongo_db, db, user, post_id)
        current_status = PostStatus(current_post["status"])

        if PostStatus.REJECTED not in VALID_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject post in state '{current_status.value}'."
            )

        team_id = current_post.get("team_id")
        if not team_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only workspace posts require approval.")

        team = db.query(Team).filter(Team.id == team_id).first()
        is_owner = team.owner_id == user.id
        is_sysadmin = user.role == UserRole.ADMINISTRATOR
        membership = db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first()
        is_team_admin = membership and membership.role == UserRole.ADMINISTRATOR

        if not (is_owner or is_sysadmin or is_team_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reject posts in this workspace.")

        now_utc = datetime.now(timezone.utc)
        res = await mongo_db["posts"].find_one_and_update(
            {"_id": ObjectId(post_id), "status": current_status.value},
            {
                "$set": {
                    "status": PostStatus.REJECTED.value,
                    "rejection_reason": reason.strip(),
                    "rejected_by": user.id,
                    "rejected_at": now_utc,
                    "updated_at": now_utc,
                }
            },
            return_document=True
        )

        if not res:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Concurrent update conflict")

        # In-App Notification to post author (fail-safe)
        try:
            post_author_id = current_post.get("user_id")
            if post_author_id and post_author_id != user.id:
                NotificationService.create_notification(
                    db=db,
                    user_id=post_author_id,
                    team_id=team_id,
                    type=NotificationType.POST_REJECTED,
                    title="Post Rejected",
                    message=f"Your post '{current_post.get('title') or 'Untitled'}' was rejected. Reason: {reason.strip()}",
                    link="/dashboard/posts"
                )
        except Exception as e:
            logger.error(f"Failed to create notification on post rejection: {e}")

        return _serialize_mongo_doc(res)
