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

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)
    base_filter: Dict[str, Any] = {
        "team_id": team_id,
        "created_at": {"$gte": period_start},
    }

    status_counts: Dict[str, int] = {}
    lifetime_total = 0
    lifetime_published = 0
    date_map: Dict[str, int] = {}
    platform_breakdown = []

    try:
        active_mongo = ensure_active_mongo_db(mongo_db)
        if active_mongo is not None:
            posts_coll = active_mongo["posts"]

            # 1. Post status counts within period
            status_pipeline = [
                {"$match": base_filter},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            status_docs = await posts_coll.aggregate(status_pipeline).to_list(length=50)
            status_counts = {d["_id"]: d["count"] for d in status_docs}

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
            for d in trend_raw:
                key = f"{d['_id']['year']:04d}-{d['_id']['month']:02d}-{d['_id']['day']:02d}"
                date_map[key] = d["count"]

            # 3. Platform breakdown (posts created in period)
            platform_pipeline = [
                {"$match": base_filter},
                {"$unwind": "$target_platforms"},
                {"$group": {"_id": "$target_platforms", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            platform_docs = await posts_coll.aggregate(platform_pipeline).to_list(length=20)
            platform_breakdown = [{"platform": d["_id"], "count": d["count"]} for d in platform_docs]
    except Exception as e:
        logger.warning(f"MongoDB query unavailable in get_overview, using resilient defaults: {e}")

    total_posts = sum(status_counts.values())
    published_posts = status_counts.get("published", 0)
    scheduled_posts = status_counts.get("scheduled", 0)
    draft_posts = status_counts.get("draft", 0)
    failed_posts = status_counts.get("failed", 0)
    pending_approval = status_counts.get("pending_approval", 0)

    daily_trend = []
    for i in range(days):
        day = (period_start + timedelta(days=i)).date()
        key = day.strftime("%Y-%m-%d")
        daily_trend.append({"date": key, "published": date_map.get(key, 0)})

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


async def get_engagement_analytics(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    days: int = 30,
    platform: Optional[str] = None,
    campaign_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Return detailed engagement analytics aggregated from post_analytics snapshots.
    Supports platform and campaign filtering.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    post_analytics_coll = mongo_db["post_analytics"]
    posts_coll = mongo_db["posts"]

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    match_filter: Dict[str, Any] = {
        "team_id": team_id,
        "recorded_at": {"$gte": period_start},
    }
    if platform:
        match_filter["platform"] = platform.lower()
    if campaign_id:
        match_filter["campaign_id"] = campaign_id

    # 1. Total Aggregation
    agg_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": None,
                "likes": {"$sum": "$likes"},
                "comments": {"$sum": "$comments"},
                "shares": {"$sum": "$shares"},
                "saves": {"$sum": "$saves"},
                "clicks": {"$sum": "$clicks"},
                "views": {"$sum": "$views"},
                "impressions": {"$sum": "$impressions"},
                "reach": {"$sum": "$reach"},
            }
        },
    ]
    agg_res = await post_analytics_coll.aggregate(agg_pipeline).to_list(length=1)
    summary_data = agg_res[0] if agg_res else {}
    likes = summary_data.get("likes", 0)
    comments = summary_data.get("comments", 0)
    shares = summary_data.get("shares", 0)
    saves = summary_data.get("saves", 0)
    clicks = summary_data.get("clicks", 0)
    views = summary_data.get("views", 0)
    impressions = summary_data.get("impressions", 0)
    reach = summary_data.get("reach", 0)
    total_engagements = likes + comments + shares + clicks
    engagement_rate = round((total_engagements / max(1, impressions) * 100), 2) if impressions > 0 else 0.0

    # 2. Daily Trend
    trend_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$recorded_at"},
                    "month": {"$month": "$recorded_at"},
                    "day": {"$dayOfMonth": "$recorded_at"},
                },
                "likes": {"$sum": "$likes"},
                "comments": {"$sum": "$comments"},
                "shares": {"$sum": "$shares"},
                "clicks": {"$sum": "$clicks"},
                "impressions": {"$sum": "$impressions"},
                "reach": {"$sum": "$reach"},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]
    trend_raw = await post_analytics_coll.aggregate(trend_pipeline).to_list(length=400)
    daily_map: Dict[str, Dict[str, int]] = {}
    for d in trend_raw:
        key = f"{d['_id']['year']:04d}-{d['_id']['month']:02d}-{d['_id']['day']:02d}"
        daily_map[key] = {
            "likes": d["likes"],
            "comments": d["comments"],
            "shares": d["shares"],
            "clicks": d["clicks"],
            "impressions": d["impressions"],
            "reach": d["reach"],
            "total_engagements": d["likes"] + d["comments"] + d["shares"] + d["clicks"],
        }

    daily_trend = []
    for i in range(days):
        day = (period_start + timedelta(days=i)).date()
        key = day.strftime("%Y-%m-%d")
        item = daily_map.get(key, {
            "likes": 0, "comments": 0, "shares": 0, "clicks": 0,
            "impressions": 0, "reach": 0, "total_engagements": 0
        })
        daily_trend.append({"date": key, **item})

    # 3. Platform Breakdown
    platform_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$platform",
                "likes": {"$sum": "$likes"},
                "comments": {"$sum": "$comments"},
                "shares": {"$sum": "$shares"},
                "clicks": {"$sum": "$clicks"},
                "impressions": {"$sum": "$impressions"},
                "reach": {"$sum": "$reach"},
            }
        },
        {"$sort": {"likes": -1}},
    ]
    platform_raw = await post_analytics_coll.aggregate(platform_pipeline).to_list(length=20)
    platform_breakdown = []
    for d in platform_raw:
        tot_eng = d["likes"] + d["comments"] + d["shares"] + d["clicks"]
        platform_breakdown.append({
            "platform": d["_id"],
            "likes": d["likes"],
            "comments": d["comments"],
            "shares": d["shares"],
            "clicks": d["clicks"],
            "impressions": d["impressions"],
            "reach": d["reach"],
            "total_engagements": tot_eng,
            "engagement_rate": round(tot_eng / max(1, d["impressions"]) * 100, 2) if d["impressions"] > 0 else 0.0,
        })

    # 4. Top Performing Posts
    top_posts_cursor = post_analytics_coll.find(match_filter).sort("likes", -1).limit(5)
    top_raw = await top_posts_cursor.to_list(length=5)
    top_posts = []
    for p in top_raw:
        post_doc = None
        try:
            from bson import ObjectId
            post_doc = await posts_coll.find_one({"_id": ObjectId(p["post_id"])})
        except Exception:
            pass
        content_snippet = post_doc.get("base_content", "")[:120] if post_doc else "Post content"
        title = post_doc.get("title") if post_doc else None
        top_posts.append({
            "post_id": p.get("post_id"),
            "title": title or content_snippet[:40] + ("..." if len(content_snippet) > 40 else ""),
            "content": content_snippet,
            "platform": p.get("platform"),
            "likes": p.get("likes", 0),
            "comments": p.get("comments", 0),
            "shares": p.get("shares", 0),
            "clicks": p.get("clicks", 0),
            "impressions": p.get("impressions", 0),
            "reach": p.get("reach", 0),
            "engagement_rate": p.get("engagement_rate", 0.0),
            "recorded_at": p.get("recorded_at").isoformat() if isinstance(p.get("recorded_at"), datetime) else str(p.get("recorded_at") or ""),
        })

    has_data = total_engagements > 0 or impressions > 0
    notice = None if has_data else (
        "No live engagement metrics recorded for this period yet. "
        "Connect social accounts and click 'Sync Analytics' to fetch latest insights."
    )

    return {
        "period_days": days,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "summary": {
            "total_engagements": total_engagements,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "saves": saves,
            "clicks": clicks,
            "views": views,
            "impressions": impressions,
            "reach": reach,
            "engagement_rate": engagement_rate,
        },
        "daily_trend": daily_trend,
        "platform_breakdown": platform_breakdown,
        "top_posts": top_posts,
        "available": True,
        "notice": notice,
    }


async def get_audience_growth(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    days: int = 30,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return audience growth and follower tracking analytics for the workspace.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    account_analytics_coll = mongo_db["account_analytics"]

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    accounts_q = db.query(SocialAccount).filter(SocialAccount.team_id == team_id)
    if platform:
        from app.models.enums import SocialPlatform
        try:
            plat_enum = SocialPlatform(platform.lower())
            accounts_q = accounts_q.filter(SocialAccount.platform == plat_enum)
        except ValueError:
            pass
    accounts = accounts_q.all()

    account_ids = [a.id for a in accounts]

    # Query latest snapshot per account
    match_filter: Dict[str, Any] = {
        "team_id": team_id,
        "recorded_at": {"$gte": period_start},
    }
    if account_ids:
        match_filter["account_id"] = {"$in": account_ids}

    pipeline = [
        {"$match": match_filter},
        {"$sort": {"recorded_at": -1}},
        {
            "$group": {
                "_id": "$account_id",
                "platform": {"$first": "$platform"},
                "latest_followers": {"$first": "$follower_count"},
                "earliest_followers": {"$last": "$follower_count"},
            }
        },
    ]
    per_account_stats = await account_analytics_coll.aggregate(pipeline).to_list(length=100)
    
    total_followers = sum(d["latest_followers"] for d in per_account_stats)
    total_initial = sum(d["earliest_followers"] for d in per_account_stats)
    net_growth = total_followers - total_initial
    growth_rate = round((net_growth / max(1, total_initial) * 100), 2) if total_initial > 0 else 0.0

    # Platform breakdown
    platform_map: Dict[str, Dict[str, Any]] = {}
    for d in per_account_stats:
        p = d["platform"]
        if p not in platform_map:
            platform_map[p] = {"platform": p, "followers": 0, "net_growth": 0}
        platform_map[p]["followers"] += d["latest_followers"]
        platform_map[p]["net_growth"] += (d["latest_followers"] - d["earliest_followers"])

    by_platform = list(platform_map.values())

    # Daily growth trend
    daily_pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$recorded_at"},
                    "month": {"$month": "$recorded_at"},
                    "day": {"$dayOfMonth": "$recorded_at"},
                },
                "total_followers": {"$sum": "$follower_count"},
                "net_growth": {"$sum": "$net_follower_growth"},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]
    daily_raw = await account_analytics_coll.aggregate(daily_pipeline).to_list(length=400)
    daily_map = {
        f"{d['_id']['year']:04d}-{d['_id']['month']:02d}-{d['_id']['day']:02d}": d
        for d in daily_raw
    }

    growth_trend = []
    current_running_followers = total_followers
    for i in range(days):
        day = (period_start + timedelta(days=i)).date()
        key = day.strftime("%Y-%m-%d")
        entry = daily_map.get(key)
        growth_trend.append({
            "date": key,
            "followers": entry["total_followers"] if entry else current_running_followers,
            "net_growth": entry["net_growth"] if entry else 0,
        })

    formatted_accounts = []
    for a in accounts:
        p_str = a.platform.value if hasattr(a.platform, "value") else str(a.platform)
        acc_stat = next((d for d in per_account_stats if d["_id"] == a.id), None)
        f_count = acc_stat["latest_followers"] if acc_stat else 0
        formatted_accounts.append({
            "account_id": a.id,
            "account_name": a.account_name,
            "platform": p_str,
            "status": a.connection_status.value if hasattr(a.connection_status, "value") else str(a.connection_status),
            "follower_count": f_count,
        })

    has_data = total_followers > 0 or len(per_account_stats) > 0
    notice = None if has_data else (
        "No audience snapshot data recorded yet. Connect accounts and run 'Sync Analytics' to capture audience metrics."
    )

    return {
        "period_days": days,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "total_followers": total_followers,
        "net_growth": net_growth,
        "growth_rate": growth_rate,
        "by_platform": by_platform,
        "growth_trend": growth_trend,
        "accounts": formatted_accounts,
        "available": True,
        "notice": notice,
    }


async def get_roi_analytics(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Compute marketing ROI, Cost Per Engagement (CPE), Cost Per Click (CPC),
    and Cost Per Mille (CPM) across all team campaigns.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    post_analytics_coll = mongo_db["post_analytics"]

    campaigns = db.query(Campaign).filter(Campaign.team_id == team_id).all()

    campaign_summaries = []
    total_budget = 0.0
    total_revenue = 0.0
    workspace_engagements = 0
    workspace_clicks = 0
    workspace_impressions = 0

    for c in campaigns:
        budget = c.budget or 0.0
        revenue = getattr(c, "revenue", 0.0) or 0.0

        # Aggregate post analytics for this campaign
        pipeline = [
            {"$match": {"team_id": team_id, "campaign_id": c.id}},
            {
                "$group": {
                    "_id": None,
                    "engagements": {"$sum": {"$add": ["$likes", "$comments", "$shares", "$clicks"]}},
                    "clicks": {"$sum": "$clicks"},
                    "impressions": {"$sum": "$impressions"},
                }
            },
        ]
        res = await post_analytics_coll.aggregate(pipeline).to_list(length=1)
        data = res[0] if res else {}
        camp_eng = data.get("engagements", 0)
        camp_clicks = data.get("clicks", 0)
        camp_imp = data.get("impressions", 0)

        # Attributed value if revenue not set
        if revenue == 0.0 and (camp_clicks > 0 or camp_eng > 0):
            revenue = round((camp_clicks * 1.50) + (camp_eng * 0.25), 2)

        net_profit = round(revenue - budget, 2)
        roi_pct = round((revenue - budget) / budget * 100, 2) if budget > 0 else None
        cpe = round(budget / camp_eng, 2) if camp_eng > 0 else None
        cpc = round(budget / camp_clicks, 2) if camp_clicks > 0 else None
        cpm = round((budget / camp_imp) * 1000, 2) if camp_imp > 0 else None

        total_budget += budget
        total_revenue += revenue
        workspace_engagements += camp_eng
        workspace_clicks += camp_clicks
        workspace_impressions += camp_imp

        campaign_summaries.append({
            "campaign_id": c.id,
            "name": c.name,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "budget": budget,
            "revenue": revenue,
            "net_profit": net_profit,
            "roi_percentage": roi_pct,
            "total_engagements": camp_eng,
            "total_clicks": camp_clicks,
            "total_impressions": camp_imp,
            "cost_per_engagement": cpe,
            "cost_per_click": cpc,
            "cost_per_mille": cpm,
        })

    workspace_net_profit = round(total_revenue - total_budget, 2)
    workspace_roi_pct = round((total_revenue - total_budget) / total_budget * 100, 2) if total_budget > 0 else None
    workspace_cpe = round(total_budget / workspace_engagements, 2) if workspace_engagements > 0 else None
    workspace_cpc = round(total_budget / workspace_clicks, 2) if workspace_clicks > 0 else None
    workspace_cpm = round((total_budget / workspace_impressions) * 1000, 2) if workspace_impressions > 0 else None

    # Sort campaigns by ROI percentage descending
    campaign_summaries.sort(key=lambda x: (x["roi_percentage"] is not None, x["roi_percentage"] or -999999), reverse=True)

    return {
        "period_days": days,
        "total_budget": round(total_budget, 2),
        "total_revenue": round(total_revenue, 2),
        "total_net_profit": workspace_net_profit,
        "overall_roi_percentage": workspace_roi_pct,
        "total_engagements": workspace_engagements,
        "total_clicks": workspace_clicks,
        "total_impressions": workspace_impressions,
        "cost_per_engagement": workspace_cpe,
        "cost_per_click": workspace_cpc,
        "cost_per_mille": workspace_cpm,
        "campaigns": campaign_summaries,
        "formula_explanation": {
            "roi": "((Revenue - Budget) / Budget) * 100 when Budget > 0",
            "cpe": "Budget / Total Engagements when Engagements > 0",
            "cpc": "Budget / Total Clicks when Clicks > 0",
            "cpm": "(Budget / Impressions) * 1000 when Impressions > 0",
        },
    }


async def compare_campaigns(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    team_id: int,
    campaign_ids: List[int],
) -> Dict[str, Any]:
    """
    Perform deep side-by-side comparison across 2 or more campaigns in a team workspace.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    posts_coll = mongo_db["posts"]
    post_analytics_coll = mongo_db["post_analytics"]

    if len(campaign_ids) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must select at least 2 campaigns to compare.")

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.team_id == team_id, Campaign.id.in_(campaign_ids))
        .all()
    )

    if len(campaigns) != len(set(campaign_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more specified campaigns were not found in this team workspace."
        )

    comparison_items = []
    for c in campaigns:
        budget = c.budget or 0.0
        revenue = getattr(c, "revenue", 0.0) or 0.0
        
        # Post counts
        total_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id})
        published_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": c.id, "status": "published"})
        pub_rate = round(published_posts / max(1, total_posts) * 100, 1) if total_posts > 0 else 0.0

        # Engagement aggregation
        pipeline = [
            {"$match": {"team_id": team_id, "campaign_id": c.id}},
            {
                "$group": {
                    "_id": None,
                    "likes": {"$sum": "$likes"},
                    "comments": {"$sum": "$comments"},
                    "shares": {"$sum": "$shares"},
                    "clicks": {"$sum": "$clicks"},
                    "views": {"$sum": "$views"},
                    "impressions": {"$sum": "$impressions"},
                    "reach": {"$sum": "$reach"},
                }
            },
        ]
        res = await post_analytics_coll.aggregate(pipeline).to_list(length=1)
        data = res[0] if res else {}
        likes = data.get("likes", 0)
        comments = data.get("comments", 0)
        shares = data.get("shares", 0)
        clicks = data.get("clicks", 0)
        views = data.get("views", 0)
        impressions = data.get("impressions", 0)
        reach = data.get("reach", 0)
        total_eng = likes + comments + shares + clicks
        eng_rate = round(total_eng / max(1, impressions) * 100, 2) if impressions > 0 else 0.0

        if revenue == 0.0 and (clicks > 0 or total_eng > 0):
            revenue = round((clicks * 1.50) + (total_eng * 0.25), 2)

        roi_pct = round((revenue - budget) / budget * 100, 2) if budget > 0 else None
        cpe = round(budget / total_eng, 2) if total_eng > 0 else None
        cpc = round(budget / clicks, 2) if clicks > 0 else None

        duration_days = None
        if c.start_date and c.end_date:
            duration_days = max(1, (c.end_date.date() - c.start_date.date()).days)

        comparison_items.append({
            "campaign_id": c.id,
            "name": c.name,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
            "target_platforms": c.target_platforms or [],
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "duration_days": duration_days,
            "budget": budget,
            "revenue": revenue,
            "total_posts": total_posts,
            "published_posts": published_posts,
            "publishing_rate": pub_rate,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "views": views,
            "impressions": impressions,
            "reach": reach,
            "total_engagements": total_eng,
            "engagement_rate": eng_rate,
            "roi_percentage": roi_pct,
            "cost_per_engagement": cpe,
            "cost_per_click": cpc,
        })

    # Identify winners
    winner_eng = max(comparison_items, key=lambda x: x["total_engagements"], default=None)
    winner_roi = max(
        [c for c in comparison_items if c["roi_percentage"] is not None],
        key=lambda x: x["roi_percentage"],
        default=None
    )
    winner_reach = max(comparison_items, key=lambda x: x["reach"], default=None)

    return {
        "campaigns": comparison_items,
        "winner_by_engagement": {
            "campaign_id": winner_eng["campaign_id"],
            "name": winner_eng["name"],
            "total_engagements": winner_eng["total_engagements"]
        } if winner_eng and winner_eng["total_engagements"] > 0 else None,
        "winner_by_roi": {
            "campaign_id": winner_roi["campaign_id"],
            "name": winner_roi["name"],
            "roi_percentage": winner_roi["roi_percentage"]
        } if winner_roi else None,
        "winner_by_reach": {
            "campaign_id": winner_reach["campaign_id"],
            "name": winner_reach["name"],
            "reach": winner_reach["reach"]
        } if winner_reach and winner_reach["reach"] > 0 else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_campaign_analytics(
    db: Session,
    mongo_db: AsyncIOMotorDatabase,
    user: User,
    campaign_id: int,
    team_id: int,
) -> Dict[str, Any]:
    """
    Fetch comprehensive analytics for an individual campaign.
    """
    _verify_team_access(db, user, team_id)
    mongo_db = ensure_active_mongo_db(mongo_db)
    posts_coll = mongo_db["posts"]
    post_analytics_coll = mongo_db["post_analytics"]

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.team_id == team_id)
        .first()
    )
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found in this team workspace."
        )

    budget = campaign.budget or 0.0
    revenue = getattr(campaign, "revenue", 0.0) or 0.0

    total_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id})
    published_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id, "status": "published"})
    scheduled_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id, "status": "scheduled"})
    failed_posts = await posts_coll.count_documents({"team_id": team_id, "campaign_id": campaign.id, "status": "failed"})
    pub_rate = round(published_posts / max(1, total_posts) * 100, 1) if total_posts > 0 else 0.0

    pipeline = [
        {"$match": {"team_id": team_id, "campaign_id": campaign.id}},
        {
            "$group": {
                "_id": None,
                "likes": {"$sum": "$likes"},
                "comments": {"$sum": "$comments"},
                "shares": {"$sum": "$shares"},
                "clicks": {"$sum": "$clicks"},
                "views": {"$sum": "$views"},
                "impressions": {"$sum": "$impressions"},
                "reach": {"$sum": "$reach"},
            }
        },
    ]
    res = await post_analytics_coll.aggregate(pipeline).to_list(length=1)
    data = res[0] if res else {}
    likes = data.get("likes", 0)
    comments = data.get("comments", 0)
    shares = data.get("shares", 0)
    clicks = data.get("clicks", 0)
    views = data.get("views", 0)
    impressions = data.get("impressions", 0)
    reach = data.get("reach", 0)
    total_eng = likes + comments + shares + clicks
    eng_rate = round(total_eng / max(1, impressions) * 100, 2) if impressions > 0 else 0.0

    if revenue == 0.0 and (clicks > 0 or total_eng > 0):
        revenue = round((clicks * 1.50) + (total_eng * 0.25), 2)

    net_profit = round(revenue - budget, 2)
    roi_pct = round((revenue - budget) / budget * 100, 2) if budget > 0 else None
    cpe = round(budget / total_eng, 2) if total_eng > 0 else None
    cpc = round(budget / clicks, 2) if clicks > 0 else None
    cpm = round((budget / impressions) * 1000, 2) if impressions > 0 else None

    return {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "status": campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
        "target_platforms": campaign.target_platforms or [],
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "budget": budget,
        "revenue": revenue,
        "posts": {
            "total": total_posts,
            "published": published_posts,
            "scheduled": scheduled_posts,
            "failed": failed_posts,
            "publishing_rate": pub_rate,
        },
        "engagement": {
            "total_engagements": total_eng,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "views": views,
            "impressions": impressions,
            "reach": reach,
            "engagement_rate": eng_rate,
        },
        "roi": {
            "spend": budget,
            "return_value": revenue,
            "net_profit": net_profit,
            "roi_percentage": roi_pct,
            "cost_per_engagement": cpe,
            "cost_per_click": cpc,
            "cost_per_mille": cpm,
        },
    }

