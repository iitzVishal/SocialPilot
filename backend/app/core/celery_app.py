import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery Application
celery_app = Celery(
    "socialpilot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.publishing", "app.tasks.email"]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,        # 5 minutes max per task
    task_soft_time_limit=240,   # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,        # Acknowledge task only after execution finishes
    task_reject_on_worker_lost=True,
    task_routes={
        "app.tasks.publishing.publish_post_task": {"queue": "publishing"},
        "app.tasks.publishing.cancel_scheduled_task": {"queue": "default"},
        "app.tasks.email.send_invitation_email_task": {"queue": "default"},
    },
    task_default_queue="default",
)

logger.info(f"Celery initialized with Redis broker: {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL}")
