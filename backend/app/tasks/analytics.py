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
