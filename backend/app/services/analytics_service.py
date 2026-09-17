"""
Analytics Service — Milestone 4 Step 3
Aggregates real internal metrics from:
- Posts (MongoDB): status, platform, timeline, campaign linkage
- Campaigns (PostgreSQL): status, post counts
- SocialAccounts (PostgreSQL): connection status, platform distribution

All data is team/workspace isolated. Authorization enforced server-side.
NOTE: External platform engagement metrics (likes, reach, comments) are NOT
      available without active OAuth scopes — those fields are clearly marked
      as UNAVAILABLE in the API response.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import User
from app.models.campaign import Campaign
from app.models.social_account import SocialAccount
from app.models.enums import SocialAccountStatus
from app.services.team_service import TeamService
from app.db.mongo import ensure_active_mongo_db

logger = logging.getLogger(__name__)


def _verify_team_access(db: Session, user: User, team_id: int) -> None:
    """Raises 403/404 if user is not a member or owner of the team."""
    TeamService.get_team_by_id(db, team_id, user)


async def get_overview(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Return a high-level analytics overview for the workspace.
    """
    _verify_team_access(db, user, team_id)

    mongo_db = ensure_active_mongo_db(mongo_db)
    posts_coll = mongo_db["posts"]

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    base_filter: Dict[str, Any] = {
        "team_id": team_id,
        "created_at": {"$gte": period_start},
    }

    # 1. Post status counts within period
    status_pipeline = [
        {"$match": base_filter},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_docs = await posts_coll.aggregate(status_pipeline).to_list(length=50)
    status_counts: Dict[str, int] = {d["_id"]: d["count"] for d in status_docs}

    total_posts = sum(status_counts.values())
    published_posts = status_counts.get("published", 0)
    scheduled_posts = status_counts.get("scheduled", 0)
    draft_posts = status_counts.get("draft", 0)
    failed_posts = status_counts.get("failed", 0)
    pending_approval = status_counts.get("pending_approval", 0)

    # Lifetime totals
    lifetime_filter = {"team_id": team_id}
    lifetime_total = await posts_coll.count_documents(lifetime_filter)
    lifetime_published = await posts_coll.count_documents({**lifetime_filter, "status": "published"})

    # 2. Daily published post trend (last N days)
    trend_pipeline = [
        {
            "$match": {
                "team_id": team_id,
                "status": "published",
                "published_at": {"$gte": period_start, "$lte": now},
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$published_at"},
                    "month": {"$month": "$published_at"},
                    "day": {"$dayOfMonth": "$published_at"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]
    trend_raw = await posts_coll.aggregate(trend_pipeline).to_list(length=200)
    date_map: Dict[str, int] = {}
    for d in trend_raw:
        key = f"{d['_id']['year']:04d}-{d['_id']['month']:02d}-{d['_id']['day']:02d}"
        date_map[key] = d["count"]

    daily_trend = []
    for i in range(days):
        day = (period_start + timedelta(days=i)).date()
        key = day.strftime("%Y-%m-%d")
        daily_trend.append({"date": key, "published": date_map.get(key, 0)})

    # 3. Platform breakdown (posts created in period)
    platform_pipeline = [
        {"$match": base_filter},
        {"$unwind": "$target_platforms"},
        {"$group": {"_id": "$target_platforms", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    platform_docs = await posts_coll.aggregate(platform_pipeline).to_list(length=20)
    platform_breakdown = [{"platform": d["_id"], "count": d["count"]} for d in platform_docs]

    # 4. Campaign summary
    campaigns = db.query(Campaign).filter(Campaign.team_id == team_id).all()
    campaign_status_counts: Dict[str, int] = {}
    for c in campaigns:
        val = c.status.value if hasattr(c.status, "value") else str(c.status)
        campaign_status_counts[val] = campaign_status_counts.get(val, 0) + 1
    total_campaigns = len(campaigns)
    active_campaigns = campaign_status_counts.get("active", 0)

    # 5. Social account health
    accounts = db.query(SocialAccount).filter(SocialAccount.team_id == team_id).all()
    total_accounts = len(accounts)
    connected_accounts = sum(
        1 for a in accounts if a.connection_status == SocialAccountStatus.CONNECTED
    )
    expired_accounts = sum(
        1 for a in accounts if a.connection_status == SocialAccountStatus.EXPIRED
    )
    error_accounts = sum(
        1 for a in accounts if a.connection_status == SocialAccountStatus.ERROR
    )
    account_platform_map: Dict[str, int] = {}
    for a in accounts:
        if a.connection_status == SocialAccountStatus.CONNECTED:
            p = a.platform.value if hasattr(a.platform, "value") else str(a.platform)
            account_platform_map[p] = account_platform_map.get(p, 0) + 1

    return {
        "period_days": days,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "posts": {
            "period_total": total_posts,
            "published": published_posts,
            "scheduled": scheduled_posts,
            "draft": draft_posts,
            "failed": failed_posts,
            "pending_approval": pending_approval,
            "lifetime_total": lifetime_total,
            "lifetime_published": lifetime_published,
            "success_rate": round(published_posts / total_posts * 100, 1) if total_posts > 0 else 0,
        },
        "daily_published_trend": daily_trend,
        "platform_breakdown": platform_breakdown,
        "campaigns": {
            "total": total_campaigns,
            "active": active_campaigns,
            "by_status": campaign_status_counts,
        },
        "accounts": {
            "total": total_accounts,
            "connected": connected_accounts,
            "expired": expired_accounts,
            "error": error_accounts,
            "by_platform": [{"platform": k, "count": v} for k, v in account_platform_map.items()],
        },
        "engagement": {
            "available": False,
            "reason": (
                "External engagement metrics (likes, reach, impressions, comments) "
                "require active OAuth scopes with each social platform provider. "
                "Connect accounts with analytics permissions to enable this feature."
            ),
        },
    }


async def get_posts_timeline(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Returns a timeline breakdown of all post activity by status within the period.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    posts_coll = mongo_db["posts"]

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    pipeline = [
        {
            "$match": {
                "team_id": team_id,
                "created_at": {"$gte": period_start},
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                    "day": {"$dayOfMonth": "$created_at"},
                    "status": "$status",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]

    raw = await posts_coll.aggregate(pipeline).to_list(length=1000)

    date_status_map: Dict[str, Dict[str, int]] = {}
    for d in raw:
        key = f"{d['_id']['year']:04d}-{d['_id']['month']:02d}-{d['_id']['day']:02d}"
        st = d["_id"]["status"]
        if key not in date_status_map:
            date_status_map[key] = {}
        date_status_map[key][st] = d["count"]

    statuses = ["draft", "scheduled", "published", "failed", "pending_approval", "cancelled"]
    series = []
    for i in range(days):
        day = (period_start + timedelta(days=i)).date()
        key = day.strftime("%Y-%m-%d")
        entry: Dict[str, Any] = {"date": key}
        day_data = date_status_map.get(key, {})
        for st in statuses:
            entry[st] = day_data.get(st, 0)
        series.append(entry)

    return {
        "period_days": days,
        "series": series,
        "statuses": statuses,
    }


async def get_campaign_performance(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
) -> Dict[str, Any]:
    """
    Returns per-campaign post publishing performance breakdown.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    posts_coll = mongo_db["posts"]

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.team_id == team_id)
        .order_by(Campaign.created_at.desc())
        .limit(20)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for c in campaigns:
        try:
            total = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id})
            published = await posts_coll.count_documents(
                {"team_id": team_id, "campaign_id": c.id, "status": "published"}
            )
            scheduled = await posts_coll.count_documents(
                {"team_id": team_id, "campaign_id": c.id, "status": "scheduled"}
            )
            failed = await posts_coll.count_documents(
                {"team_id": team_id, "campaign_id": c.id, "status": "failed"}
            )
        except Exception as e:
            logger.warning(f"Failed to fetch analytics for campaign {c.id}: {e}")
            total = published = scheduled = failed = 0

        items.append({
            "campaign_id": c.id,
            "name": c.name,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "target_platforms": c.target_platforms or [],
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "total_posts": total,
            "published_posts": published,
            "scheduled_posts": scheduled,
            "failed_posts": failed,
            "publish_rate": round(published / total * 100, 1) if total > 0 else 0,
        })

    return {"campaigns": items, "total": len(items)}
