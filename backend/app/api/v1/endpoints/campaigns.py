from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api import deps
from app.models.user import User
from app.models.enums import CampaignStatus
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignComparisonRequest,
)
from app.services.campaign_service import CampaignService
from app.services.post_service import PostService
from app.services import analytics_service
from app.db.mongo import get_mongo_db

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Create a new campaign for a team workspace."""
    return await CampaignService.create_campaign(
        db=db,
        user=current_user,
        campaign_in=campaign_in,
        team_id=team_id
    )


@router.get("", response_model=Dict[str, Any])
async def list_campaigns(
    team_id: int = Query(..., description="Target team workspace ID"),
    status: Optional[CampaignStatus] = Query(None, description="Optional status filter"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """List paginated campaigns for a team workspace."""
    return await CampaignService.list_campaigns(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        status_filter=status,
        page=page,
        limit=limit
    )


@router.post("/compare", response_model=Dict[str, Any])
async def compare_campaigns_post(
    comparison_req: CampaignComparisonRequest,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Compare multiple campaigns side-by-side on performance, engagement, reach, and ROI.
    """
    return await analytics_service.compare_campaigns(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        campaign_ids=comparison_req.campaign_ids
    )


@router.get("/compare", response_model=Dict[str, Any])
async def compare_campaigns_get(
    campaign_ids: str = Query(..., description="Comma-separated campaign IDs to compare, e.g. '1,2'"),
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Compare multiple campaigns via GET with comma-separated campaign_ids query parameter.
    """
    try:
        c_ids = [int(x.strip()) for x in campaign_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="campaign_ids must be a comma-separated list of integers.")
    
    return await analytics_service.compare_campaigns(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        campaign_ids=c_ids
    )


@router.get("/{campaign_id}", response_model=Dict[str, Any])
async def get_campaign(
    campaign_id: int,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Get details for a specific campaign."""
    return await CampaignService.get_campaign(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        campaign_id=campaign_id,
        team_id=team_id
    )


@router.get("/{campaign_id}/analytics", response_model=Dict[str, Any])
async def get_campaign_analytics_endpoint(
    campaign_id: int,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Get detailed engagement, reach, post performance, and ROI analytics for a campaign."""
    return await analytics_service.get_campaign_analytics(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        campaign_id=campaign_id,
        team_id=team_id
    )


@router.put("/{campaign_id}", response_model=Dict[str, Any])
async def update_campaign(
    campaign_id: int,
    campaign_in: CampaignUpdate,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Update an existing campaign."""
    return await CampaignService.update_campaign(
        db=db,
        user=current_user,
        campaign_id=campaign_id,
        team_id=team_id,
        campaign_in=campaign_in
    )


@router.delete("/{campaign_id}", response_model=Dict[str, Any])
async def delete_campaign(
    campaign_id: int,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Delete a campaign and unlink associated posts."""
    return await CampaignService.delete_campaign(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        campaign_id=campaign_id,
        team_id=team_id
    )


@router.get("/{campaign_id}/posts", response_model=Dict[str, Any])
async def get_campaign_posts(
    campaign_id: int,
    team_id: int = Query(..., description="Target team workspace ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Get posts associated with a specific campaign."""
    # Verify campaign access
    await CampaignService.get_campaign(db, mongo_db, current_user, campaign_id, team_id)
    
    # Query posts by team_id and campaign_id
    posts, total = await PostService.list_posts(
        mongo_db=mongo_db,
        db=db,
        user=current_user,
        team_id=team_id,
        campaign_id=campaign_id,
        skip=(page - 1) * limit,
        limit=limit
    )
    total_pages = max(1, (total + limit - 1) // limit)
    return {
        "items": posts,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.post("/{campaign_id}/posts/{post_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def attach_post_to_campaign(
    campaign_id: int,
    post_id: str,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Attach an existing post to a campaign within the same team workspace."""
    # 1. Verify campaign access
    campaign = await CampaignService.get_campaign(db, mongo_db, current_user, campaign_id, team_id)

    # 2. Verify post access and ownership
    post = await PostService.get_post_by_id(mongo_db, db, current_user, post_id)
    if post.get("team_id") != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot attach post from a different team workspace."
        )

    # 3. Associate post with campaign in MongoDB
    await mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"campaign_id": campaign_id, "updated_at": datetime.now(timezone.utc)}}
    )

    # 4. Associate any post analytics with this campaign
    await mongo_db["post_analytics"].update_many(
        {"post_id": post_id},
        {"$set": {"campaign_id": campaign_id}}
    )

    return {
        "message": "Post successfully attached to campaign",
        "post_id": post_id,
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name")
    }


@router.delete("/{campaign_id}/posts/{post_id}", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def detach_post_from_campaign(
    campaign_id: int,
    post_id: str,
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Detach a post from a campaign (unlinks without deleting the post)."""
    # 1. Verify campaign access
    await CampaignService.get_campaign(db, mongo_db, current_user, campaign_id, team_id)

    # 2. Verify post access
    post = await PostService.get_post_by_id(mongo_db, db, current_user, post_id)
    if post.get("campaign_id") != campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Post {post_id} is not associated with campaign {campaign_id}."
        )

    # 3. Detach post
    await mongo_db["posts"].update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"campaign_id": None, "updated_at": datetime.now(timezone.utc)}}
    )

    # 4. Detach post analytics
    await mongo_db["post_analytics"].update_many(
        {"post_id": post_id, "campaign_id": campaign_id},
        {"$set": {"campaign_id": None}}
    )

    return {
        "message": "Post successfully detached from campaign",
        "post_id": post_id,
        "campaign_id": campaign_id
    }
