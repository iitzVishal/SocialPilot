import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.social_account import SocialAccount
from app.models.enums import SocialPlatform, SocialAccountStatus
from app.models.instagram_data import (
    InstagramMetricSnapshot,
    InstagramMedia,
    InstagramComment,
    MetaWebhookEvent,
)
from app.core.security import decrypt_token
from app.integrations import get_platform_adapter

logger = logging.getLogger(__name__)


class InstagramCommandService:
    """
    Authoritative service managing Instagram Command Center operations:
    - Real-time & periodic synchronization
    - Relational PostgreSQL historical metric snapshots
    - Media synchronization and engagement aggregation
    - Deterministic SocialPilot Performance Score computation
    - Comment synchronization and moderation
    """

    @staticmethod
    def calculate_performance_score(
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        saved: int = 0,
        reach: int = 0,
        follower_count: int = 0
    ) -> float:
        """
        Deterministic SocialPilot Performance Score formula (0.0 to 100.0).
        Weighted formula:
          Weight(likes) = 1.0
          Weight(comments) = 2.5
          Weight(shares) = 3.0
          Weight(saved) = 2.0
          Weight(reach) = 0.02
        Normalized against follower base (or raw volume if audience size is unavailable).
        """
        raw_weighted = (likes * 1.0) + (comments * 2.5) + (shares * 3.0) + (saved * 2.0) + (reach * 0.02)
        if follower_count > 0:
            audience_factor = max(1.0, follower_count * 0.01)
            score = (raw_weighted / audience_factor) * 10.0
        else:
            score = raw_weighted * 0.5

        return round(min(100.0, max(0.0, score)), 2)

    @staticmethod
    def sync_instagram_account(db: Session, account: SocialAccount) -> Dict[str, Any]:
        """
        Synchronize Instagram account with real Meta Graph API responses.
        Updates SocialAccount, InstagramMetricSnapshot, and InstagramMedia in PostgreSQL.
        """
        if account.platform != SocialPlatform.INSTAGRAM:
            raise ValueError(f"Account {account.id} is not an Instagram account.")

        now_utc = datetime.now(timezone.utc)
        today_date = now_utc.date()

        account.sync_status = "syncing"
        account.connection_status = SocialAccountStatus.SYNCING
        db.commit()

        adapter = get_platform_adapter(SocialPlatform.INSTAGRAM)
        try:
            token = decrypt_token(account.access_token) if account.access_token else ""
        except Exception as e:
            logger.warning(f"Error decrypting token for account {account.id}: {e}")
            token = account.access_token or ""

        try:
            # 1. Fetch live profile & audience data
            profile_data = adapter.synchronize_account_data(token, account.account_identifier)
            if profile_data.get("status") == "error":
                account.sync_status = "error"
                account.last_failed_sync_at = now_utc
                account.sync_error = profile_data.get("message", "Meta Graph API sync error")
                if profile_data.get("is_revoked"):
                    account.connection_status = SocialAccountStatus.REVOKED
                elif profile_data.get("is_token_expired"):
                    account.connection_status = SocialAccountStatus.AUTHORIZATION_EXPIRED
                else:
                    account.connection_status = SocialAccountStatus.NEEDS_ATTENTION
                db.commit()
                return profile_data

            # Update account metadata
            account.account_name = profile_data.get("username") or profile_data.get("account_name") or account.account_name
            current_perms = dict(account.platform_permissions or {})
            if profile_data.get("avatar_url"):
                current_perms["avatar_url"] = profile_data["avatar_url"]
                current_perms["profile_picture_url"] = profile_data["avatar_url"]
            if profile_data.get("biography"):
                current_perms["biography"] = profile_data["biography"]

            follower_count = int(profile_data.get("follower_count") or 0)
            following_count = int(profile_data.get("following_count") or 0)
            media_count = int(profile_data.get("post_count") or 0)

            current_perms["follower_count"] = follower_count
            current_perms["following_count"] = following_count
            current_perms["post_count"] = media_count
            current_perms["sync_status"] = "synchronized"
            current_perms.pop("sync_error", None)

            # 2. Fetch Account Insights (impressions, reach, profile views, website clicks)
            insights = adapter.fetch_account_insights(token, account.account_identifier)
            impressions = insights.get("impressions", 0)
            reach = insights.get("reach", 0)
            profile_views = insights.get("profile_views", 0)
            website_clicks = insights.get("website_clicks", 0)

            # 3. Store / Upsert Daily Historical Metric Snapshot in PostgreSQL
            prev_snapshot = (
                db.query(InstagramMetricSnapshot)
                .filter(InstagramMetricSnapshot.account_id == account.id, InstagramMetricSnapshot.date < today_date)
                .order_by(desc(InstagramMetricSnapshot.date))
                .first()
            )
            prev_followers = prev_snapshot.follower_count if prev_snapshot else follower_count
            net_growth = follower_count - prev_followers
            growth_rate = round((net_growth / max(1, prev_followers)) * 100, 2) if prev_followers > 0 else 0.0

            existing_today_snapshot = (
                db.query(InstagramMetricSnapshot)
                .filter(InstagramMetricSnapshot.account_id == account.id, InstagramMetricSnapshot.date == today_date)
                .first()
            )

            if existing_today_snapshot:
                existing_today_snapshot.follower_count = follower_count
                existing_today_snapshot.following_count = following_count
                existing_today_snapshot.media_count = media_count
                existing_today_snapshot.net_follower_growth = net_growth
                existing_today_snapshot.growth_rate = growth_rate
                existing_today_snapshot.impressions = impressions
                existing_today_snapshot.reach = reach
                existing_today_snapshot.profile_views = profile_views
                existing_today_snapshot.website_clicks = website_clicks
                existing_today_snapshot.recorded_at = now_utc
            else:
                new_snapshot = InstagramMetricSnapshot(
                    account_id=account.id,
                    team_id=account.team_id,
                    date=today_date,
                    follower_count=follower_count,
                    following_count=following_count,
                    media_count=media_count,
                    net_follower_growth=net_growth,
                    growth_rate=growth_rate,
                    impressions=impressions,
                    reach=reach,
                    profile_views=profile_views,
                    website_clicks=website_clicks,
                    recorded_at=now_utc
                )
                db.add(new_snapshot)

            # 4. Synchronize Recent Published Media
            raw_media_items = adapter.fetch_recent_posts(token, account.account_identifier, limit=50)
            synced_media_count = 0

            for m in raw_media_items:
                ext_id = m.get("external_post_id")
                if not ext_id:
                    continue

                likes = int(m.get("likes") or 0)
                comments = int(m.get("comments") or 0)
                media_type = (m.get("media_type") or "IMAGE").upper()
                caption = m.get("caption") or ""
                permalink = m.get("permalink") or ""
                thumb = m.get("thumbnail_url")
                raw_ts = m.get("created_time")
                parsed_ts = None
                if raw_ts:
                    try:
                        parsed_ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Fetch media insights where available
                m_insights = adapter.fetch_media_insights(token, ext_id)
                m_reach = m_insights.get("reach", 0)
                m_saved = m_insights.get("saved", 0)
                m_shares = m_insights.get("shares", 0)
                m_views = m_insights.get("views", 0)

                # Compute SocialPilot Performance Score
                perf_score = InstagramCommandService.calculate_performance_score(
                    likes=likes,
                    comments=comments,
                    shares=m_shares,
                    saved=m_saved,
                    reach=m_reach,
                    follower_count=follower_count
                )

                existing_media = (
                    db.query(InstagramMedia)
                    .filter(InstagramMedia.account_id == account.id, InstagramMedia.external_media_id == ext_id)
                    .first()
                )

                if existing_media:
                    existing_media.caption = caption
                    existing_media.media_type = media_type
                    existing_media.permalink = permalink
                    existing_media.thumbnail_url = thumb
                    existing_media.like_count = likes
                    existing_media.comments_count = comments
                    existing_media.views_count = m_views
                    existing_media.reach_count = m_reach
                    existing_media.shares_count = m_shares
                    existing_media.saved_count = m_saved
                    existing_media.engagement = likes + comments
                    existing_media.performance_score = perf_score
                    existing_media.raw_insights = m_insights
                    existing_media.updated_at = now_utc
                else:
                    new_media = InstagramMedia(
                        account_id=account.id,
                        external_media_id=ext_id,
                        caption=caption,
                        media_type=media_type,
                        permalink=permalink,
                        thumbnail_url=thumb,
                        timestamp=parsed_ts,
                        like_count=likes,
                        comments_count=comments,
                        views_count=m_views,
                        reach_count=m_reach,
                        shares_count=m_shares,
                        saved_count=m_saved,
                        engagement=likes + comments,
                        performance_score=perf_score,
                        raw_insights=m_insights,
                        created_at=now_utc,
                        updated_at=now_utc
                    )
                    db.add(new_media)

                synced_media_count += 1

            # 5. Finalize Account State
            account.platform_permissions = current_perms
            account.connection_status = SocialAccountStatus.CONNECTED
            account.last_synced_at = now_utc
            account.sync_status = "idle"
            account.sync_error = None

            db.commit()
            db.refresh(account)

            logger.info(f"Successfully synchronized Instagram account {account.id} (@{account.account_name}): {synced_media_count} media items, snapshot recorded.")
            return {
                "status": "success",
                "account_id": account.id,
                "account_name": account.account_name,
                "follower_count": follower_count,
                "media_count": media_count,
                "synced_media_count": synced_media_count,
                "last_synced_at": now_utc.isoformat()
            }

        except Exception as e:
            db.rollback()
            err_msg = str(e)
            logger.error(f"Failed to synchronize Instagram account {account.id}: {err_msg}", exc_info=True)
            account.sync_status = "error"
            account.last_failed_sync_at = now_utc
            account.sync_error = err_msg
            account.connection_status = SocialAccountStatus.NEEDS_ATTENTION
            db.commit()
            return {
                "status": "error",
                "account_id": account.id,
                "message": err_msg
            }

    @staticmethod
    def get_historical_snapshots(db: Session, account_id: int, days: int = 30) -> List[InstagramMetricSnapshot]:
        """Fetch historical snapshots ordered chronologically for charts & growth analysis."""
        cutoff_date = date.today() - timedelta(days=days)
        return (
            db.query(InstagramMetricSnapshot)
            .filter(InstagramMetricSnapshot.account_id == account_id, InstagramMetricSnapshot.date >= cutoff_date)
            .order_by(InstagramMetricSnapshot.date.asc())
            .all()
        )

    @staticmethod
    def get_top_media(
        db: Session,
        account_id: int,
        media_type: Optional[str] = None,
        sort_by: str = "performance_score",
        limit: int = 25
    ) -> List[InstagramMedia]:
        """Fetch media for an account sorted by performance score, engagement, or recency."""
        query = db.query(InstagramMedia).filter(InstagramMedia.account_id == account_id)
        if media_type:
            query = query.filter(InstagramMedia.media_type == media_type.upper())

        if sort_by == "engagement":
            query = query.order_by(desc(InstagramMedia.engagement))
        elif sort_by == "likes":
            query = query.order_by(desc(InstagramMedia.like_count))
        elif sort_by == "comments":
            query = query.order_by(desc(InstagramMedia.comments_count))
        elif sort_by == "recent":
            query = query.order_by(desc(InstagramMedia.timestamp))
        else:
            query = query.order_by(desc(InstagramMedia.performance_score))

        return query.limit(limit).all()

    @staticmethod
    def compute_account_performance_score(db: Session, account_id: int) -> Dict[str, Any]:
        """
        Aggregate recent media performance into an authoritative account-level SocialPilot Performance Score.
        """
        media_list = db.query(InstagramMedia).filter(InstagramMedia.account_id == account_id).limit(50).all()
        if not media_list:
            return {
                "account_id": account_id,
                "score": 0.0,
                "grade": "Developing",
                "formula_description": "SocialPilot Performance Score: weighted combination of engagement, reach, saves, and comments normalized against audience.",
                "breakdown": {
                    "likes": 0, "comments": 0, "views": 0, "reach": 0, "saves": 0, "shares": 0, "engagement_rate": 0.0
                }
            }

        total_likes = sum(m.like_count for m in media_list)
        total_comments = sum(m.comments_count for m in media_list)
        total_views = sum(m.views_count for m in media_list)
        total_reach = sum(m.reach_count for m in media_list)
        total_saves = sum(m.saved_count for m in media_list)
        total_shares = sum(m.shares_count for m in media_list)

        avg_score = round(sum(m.performance_score for m in media_list) / len(media_list), 2)

        # Categorize grade
        if avg_score >= 80.0:
            grade = "Excellent"
        elif avg_score >= 60.0:
            grade = "Strong"
        elif avg_score >= 40.0:
            grade = "Good"
        elif avg_score >= 20.0:
            grade = "Fair"
        else:
            grade = "Developing"

        total_eng = total_likes + total_comments
        eng_rate = round((total_eng / max(1, total_reach)) * 100, 2) if total_reach > 0 else 0.0

        return {
            "account_id": account_id,
            "score": avg_score,
            "grade": grade,
            "formula_description": "SocialPilot Performance Score: weighted combination of engagement, reach, saves, and comments normalized against audience.",
            "breakdown": {
                "likes": total_likes,
                "comments": total_comments,
                "views": total_views,
                "reach": total_reach,
                "saves": total_saves,
                "shares": total_shares,
                "engagement_rate": eng_rate
            }
        }
