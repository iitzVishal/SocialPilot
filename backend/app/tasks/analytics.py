import asyncio
import logging
from typing import Dict, Any, Optional
from celery import Task

from app.core.celery_app import celery_app
from app.db.postgres import SessionLocal
from app.core.config import settings
from app.services.analytics_ingestion_service import AnalyticsIngestionService
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class AnalyticsSyncTask(Task):
    """Custom task wrapper providing automatic retry and error tracking."""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True


@celery_app.task(bind=True, base=AnalyticsSyncTask, name="app.tasks.analytics.sync_team_analytics_task")
def sync_team_analytics_task(self, team_id: int) -> Dict[str, Any]:
    """
    Celery background worker task for synchronizing social media analytics for a workspace.
    """
    logger.info(f"[Celery Worker] Starting sync_team_analytics_task for team_id: {team_id}")
    db = SessionLocal()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongo_db = client[settings.MONGODB_DB_NAME]

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            AnalyticsIngestionService.sync_team_analytics(db, mongo_db, team_id)
        )
        logger.info(f"[Celery Worker] Finished sync_team_analytics_task for team_id: {team_id}. Result: {result}")
        return result
    except Exception as e:
        logger.error(f"[Celery Worker] Error executing sync_team_analytics_task for team_id {team_id}: {str(e)}", exc_info=True)
        raise e
    finally:
        db.close()
        client.close()


@celery_app.task(bind=True, base=AnalyticsSyncTask, name="app.tasks.analytics.sync_instagram_account_task")
def sync_instagram_account_task(self, account_id: int) -> Dict[str, Any]:
    """
    Background worker task to execute initial or on-demand Instagram synchronization asynchronously.
    """
    logger.info(f"[Celery Worker] Starting sync_instagram_account_task for account_id: {account_id}")
    db = SessionLocal()
    try:
        from app.models.social_account import SocialAccount
        from app.services.instagram_command_service import InstagramCommandService

        account = db.query(SocialAccount).filter(SocialAccount.id == account_id).first()
        if not account:
            logger.warning(f"SocialAccount {account_id} not found for sync.")
            return {"status": "error", "message": f"Account {account_id} not found"}

        result = InstagramCommandService.sync_instagram_account(db, account)
        logger.info(f"[Celery Worker] Completed sync_instagram_account_task for account_id: {account_id}")
        return result
    except Exception as e:
        logger.error(f"[Celery Worker] Error executing sync_instagram_account_task for {account_id}: {e}", exc_info=True)
        raise e
    finally:
        db.close()


@celery_app.task(bind=True, base=AnalyticsSyncTask, name="app.tasks.analytics.periodic_sync_instagram_accounts_task")
def periodic_sync_instagram_accounts_task(self) -> Dict[str, Any]:
    """
    Celery Beat periodic task: continuously synchronizes all active Instagram accounts
    with exponential backoff and rate limit consideration.
    """
    import time
    logger.info("[Celery Worker] Starting periodic_sync_instagram_accounts_task")
    db = SessionLocal()
    try:
        from app.models.social_account import SocialAccount
        from app.models.enums import SocialPlatform, SocialAccountStatus
        from app.services.instagram_command_service import InstagramCommandService

        accounts = (
            db.query(SocialAccount)
            .filter(
                SocialAccount.platform == SocialPlatform.INSTAGRAM,
                SocialAccount.connection_status.in_([
                    SocialAccountStatus.CONNECTED,
                    SocialAccountStatus.SYNCING,
                    SocialAccountStatus.NEEDS_ATTENTION
                ])
            )
            .all()
        )

        synced = 0
        failed = 0
        for acc in accounts:
            try:
                res = InstagramCommandService.sync_instagram_account(db, acc)
                if res.get("status") == "success":
                    synced += 1
                else:
                    failed += 1
            except Exception as acc_err:
                logger.warning(f"Periodic sync failed for account {acc.id}: {acc_err}")
                failed += 1
            # Respect Meta rate limits by staggering calls
            time.sleep(1.0)

        logger.info(f"[Celery Worker] Periodic sync finished: {synced} succeeded, {failed} failed.")
        return {"synced": synced, "failed": failed, "total": len(accounts)}
    finally:
        db.close()

