"""
Analytics API Endpoints — Milestone 4 Step 3
All endpoints are team-scoped and RBAC-enforced.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api import deps
from app.models.user import User
from app.db.mongo import get_mongo_db
from app.services import analytics_service
from app.services.analytics_ingestion_service import AnalyticsIngestionService

router = APIRouter()


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
    account_id: Optional[int] = Query(None, description="Optional social account ID filter"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return workspace-level or account-specific analytics overview.
    """
    return await analytics_service.get_overview(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
        account_id=account_id,
    )


@router.get("/posts/timeline", response_model=Dict[str, Any])
async def get_posts_timeline(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return daily post activity breakdown by status for the workspace.
    """
    return await analytics_service.get_posts_timeline(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
    )


@router.get("/posts/performance", response_model=Dict[str, Any])
async def get_posts_performance_endpoint(
    team_id: int = Query(..., description="Target team workspace ID"),
    account_id: Optional[int] = Query(None, description="Optional social account ID filter"),
    platform: Optional[str] = Query(None, description="Optional platform filter"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(25, ge=1, le=100, description="Page limit"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return paginated list of social posts and published media along with their engagement metrics.
    """
    return await analytics_service.get_post_performance(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        account_id=account_id,
        platform=platform,
        days=days,
        limit=limit,
        skip=skip,
    )


@router.get("/campaigns/performance", response_model=Dict[str, Any])
async def get_campaign_performance(
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return per-campaign post publishing performance (total, published, scheduled, failed).
    """
    return await analytics_service.get_campaign_performance(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
    )


@router.get("/engagement", response_model=Dict[str, Any])
async def get_engagement_analytics_endpoint(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    platform: Optional[str] = Query(None, description="Optional platform filter (facebook, instagram, etc.)"),
    campaign_id: Optional[int] = Query(None, description="Optional campaign ID filter"),
    account_id: Optional[int] = Query(None, description="Optional social account ID filter"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return normalized engagement analytics including likes, comments, shares,
    clicks, views, impressions, reach, engagement rate, daily trends, and top posts.
    """
    return await analytics_service.get_engagement_analytics(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
        platform=platform,
        campaign_id=campaign_id,
        account_id=account_id,
    )


@router.get("/audience", response_model=Dict[str, Any])
async def get_audience_growth_endpoint(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    platform: Optional[str] = Query(None, description="Optional platform filter"),
    account_id: Optional[int] = Query(None, description="Optional social account ID filter"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return audience growth, follower counts, net follower growth, and growth trends over time.
    """
    return await analytics_service.get_audience_growth(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
        platform=platform,
        account_id=account_id,
    )


@router.get("/roi", response_model=Dict[str, Any])
async def get_roi_analytics_endpoint(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return marketing ROI metrics: campaign spend vs return, ROI %, Cost Per Engagement (CPE),
    Cost Per Click (CPC), and Cost Per Mille (CPM).
    """
    return await analytics_service.get_roi_analytics(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
    )


@router.post("/sync", response_model=Dict[str, Any])
async def sync_workspace_analytics(
    team_id: int = Query(..., description="Target team workspace ID"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Trigger live social platform analytics ingestion across all connected accounts in the workspace.
    """
    # Enforce team membership
    from app.services.team_service import TeamService
    TeamService.get_team_by_id(db, team_id, current_user)

    return await AnalyticsIngestionService.sync_team_analytics(
        db=db,
        mongo_db=mongo_db,
        team_id=team_id,
    )

