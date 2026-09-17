import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, UserRole, NotificationType
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignListResponse
from app.services.team_service import TeamService
from app.services.notification_service import NotificationService
from app.db.mongo import ensure_active_mongo_db


logger = logging.getLogger(__name__)


class CampaignService:

    @staticmethod
    async def create_campaign(
        db: Session,
        user: User,
        campaign_in: CampaignCreate,
        team_id: int
    ) -> Dict[str, Any]:
        """Create a new marketing campaign for a team."""
        # 1. Enforce team membership / authorization
        TeamService.get_team_by_id(db, team_id, user)
        
        # 2. Instantiate Campaign record
        platforms_list = [p.value if hasattr(p, "value") else str(p) for p in campaign_in.target_platforms]
        campaign = Campaign(
            team_id=team_id,
            name=campaign_in.name,
            description=campaign_in.description,
            objective=campaign_in.objective,
            target_platforms=platforms_list,
            start_date=campaign_in.start_date,
            end_date=campaign_in.end_date,
            budget=campaign_in.budget or 0.0,
            status=campaign_in.status or CampaignStatus.DRAFT,
            created_by=user.id,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        res = CampaignResponse.model_validate(campaign)
        res_dict = res.model_dump()
        res_dict["target_platforms"] = platforms_list
        res_dict["post_count"] = 0
        res_dict["published_post_count"] = 0
        res_dict["scheduled_post_count"] = 0

        # In-App Notification (fail-safe)
        try:
            memberships = db.query(TeamMember).filter_by(team_id=team_id).all()
            user_ids = [m.user_id for m in memberships if m.user_id != user.id]
            NotificationService.create_notifications_for_users(
                db=db,
                user_ids=user_ids,
                team_id=team_id,
                type=NotificationType.CAMPAIGN_CREATED,
                title="New Campaign Created",
                message=f"Campaign '{campaign.name}' was created.",
                link=f"/dashboard/campaigns/{campaign.id}"
            )
        except Exception as e:
            logger.error(f"Failed to create campaign notification: {e}")

        return res_dict

    @staticmethod
    async def list_campaigns(
        db: Session,
        mongo_db: AsyncIOMotorDatabase,
        user: User,
        team_id: int,
        status_filter: Optional[CampaignStatus] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """List paginated campaigns for a specific team with post counts."""
        # 1. Enforce team membership
        TeamService.get_team_by_id(db, team_id, user)

        query = db.query(Campaign).filter(Campaign.team_id == team_id)
        if status_filter:
            query = query.filter(Campaign.status == status_filter)

        total = query.count()
        total_pages = max(1, (total + limit - 1) // limit)
        offset = (page - 1) * limit
        campaigns = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit).all()

        mongo_db = ensure_active_mongo_db(mongo_db)
        posts_coll = mongo_db["posts"]

        items = []
        for c in campaigns:
            c_dict = CampaignResponse.model_validate(c).model_dump()
            c_dict["target_platforms"] = c.target_platforms or []
            
            # Count posts linked to this campaign
            try:
                total_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id})
                published_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id, "status": "published"})
                scheduled_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id, "status": "scheduled"})
            except Exception as e:
                logger.warning(f"Error fetching post count for campaign {c.id}: {e}")
                total_posts = 0
                published_posts = 0
                scheduled_posts = 0

            c_dict["post_count"] = total_posts
            c_dict["published_post_count"] = published_posts
            c_dict["scheduled_post_count"] = scheduled_posts
            items.append(c_dict)

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

    @staticmethod
    async def get_campaign(
        db: Session,
        mongo_db: AsyncIOMotorDatabase,
        user: User,
        campaign_id: int,
        team_id: int
    ) -> Dict[str, Any]:
        """Fetch details for a specific campaign."""
        TeamService.get_team_by_id(db, team_id, user)

        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.team_id == team_id
        ).first()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found in workspace."
            )

        c_dict = CampaignResponse.model_validate(campaign).model_dump()
        c_dict["target_platforms"] = campaign.target_platforms or []

        mongo_db = ensure_active_mongo_db(mongo_db)
        posts_coll = mongo_db["posts"]

        try:
            c_dict["post_count"] = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id})
            c_dict["published_post_count"] = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id, "status": "published"})
            c_dict["scheduled_post_count"] = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id, "status": "scheduled"})
        except Exception:
            c_dict["post_count"] = 0
            c_dict["published_post_count"] = 0
            c_dict["scheduled_post_count"] = 0

        return c_dict

    @staticmethod
    async def update_campaign(
        db: Session,
        user: User,
        campaign_id: int,
        team_id: int,
        campaign_in: CampaignUpdate
    ) -> Dict[str, Any]:
        """Update an existing campaign."""
        TeamService.get_team_by_id(db, team_id, user)

        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.team_id == team_id
        ).first()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found in workspace."
            )

        update_data = campaign_in.model_dump(exclude_unset=True)
        if "target_platforms" in update_data and update_data["target_platforms"] is not None:
            update_data["target_platforms"] = [p.value if hasattr(p, "value") else str(p) for p in update_data["target_platforms"]]

        for field, val in update_data.items():
            setattr(campaign, field, val)

        db.commit()
        db.refresh(campaign)

        res = CampaignResponse.model_validate(campaign)
        res_dict = res.model_dump()
        res_dict["target_platforms"] = campaign.target_platforms or []
        return res_dict

    @staticmethod
    async def delete_campaign(
        db: Session,
        mongo_db: AsyncIOMotorDatabase,
        user: User,
        campaign_id: int,
        team_id: int
    ) -> Dict[str, Any]:
        """Delete a campaign and un-assign associated posts."""
        TeamService.get_team_by_id(db, team_id, user)

        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.team_id == team_id
        ).first()

        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found in workspace."
            )

        # Unlink campaign from posts in MongoDB
        mongo_db = ensure_active_mongo_db(mongo_db)
        posts_coll = mongo_db["posts"]
        try:
            await posts_coll.update_many(
                {"team_id": team_id, "campaign_id": campaign.id},
                {"$set": {"campaign_id": None}}
            )
        except Exception as e:
            logger.warning(f"Failed to unlink posts from deleted campaign {campaign_id}: {e}")

        db.delete(campaign)
        db.commit()

        return {"status": "success", "message": f"Campaign {campaign_id} deleted successfully."}
