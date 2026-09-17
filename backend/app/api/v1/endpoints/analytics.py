"""
Analytics API Endpoints — Milestone 4 Step 3
All endpoints are team-scoped and RBAC-enforced.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api import deps
from app.models.user import User
from app.db.mongo import get_mongo_db
from app.services import analytics_service

router = APIRouter()


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview(
    team_id: int = Query(..., description="Target team workspace ID"),
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
    db: Session = Depends(deps.get_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Return workspace-level analytics overview.

    Includes:
    - Post counts by status (current period + lifetime)
    - Daily published post trend
    - Platform breakdown (posts per platform)
    - Campaign summary
    - Social account health

    Note: External engagement metrics (likes, reach) are NOT available unless
    the social accounts are connected with analytics OAuth scopes.
    """
    return await analytics_service.get_overview(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
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
    Useful for rendering stacked bar / area charts.
    """
    return await analytics_service.get_posts_timeline(
        db=db,
        mongo_db=mongo_db,
        user=current_user,
        team_id=team_id,
        days=days,
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
