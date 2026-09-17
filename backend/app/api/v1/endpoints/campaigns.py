from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api import deps
from app.models.user import User
from app.models.enums import CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, CampaignListResponse
from app.services.campaign_service import CampaignService
from app.services.post_service import PostService
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
