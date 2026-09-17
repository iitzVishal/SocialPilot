import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from celery import Task
from app.core.celery_app import celery_app
from app.db.postgres import SessionLocal
from app.models.social_account import SocialAccount
from app.models.enums import PostStatus, PublishResultStatus, SocialAccountStatus
from app.schemas.post import AccountPublishResult
from app.services.post_service import PostService
from app.services.adapters import get_platform_adapter
from app.db.mongo import get_mongo_db

logger = logging.getLogger(__name__)


async def _async_publish_post_execution(post_id: str, account_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Asynchronous business workflow for background post publishing.
    Executes atomic state claim, platform adapters dispatch, and result persistence.
    """
    db = SessionLocal()
    mongo_db = get_mongo_db()

    try:
        # 1. Atomic claim for publishing (transitions QUEUED/SCHEDULED -> PUBLISHING)
        claimed_post = await PostService.atomic_claim_for_publishing(mongo_db=mongo_db, post_id=post_id)
        if not claimed_post:
            logger.warning(f"Post {post_id} could not be claimed for publishing (may be cancelled or already publishing).")
            return {"post_id": post_id, "status": "SKIPPED_OR_ALREADY_CLAIMED"}

        # 2. Extract content, media, customizations, and target accounts
        target_account_ids = account_ids if account_ids is not None else (
            claimed_post.get("target_accounts") or claimed_post.get("target_account_ids") or []
        )
        content = claimed_post.get("base_content") or claimed_post.get("content") or ""
        media = claimed_post.get("media_attachments") or claimed_post.get("media") or []
        platform_customizations = claimed_post.get("platform_customizations", {}) or {}

        # 3. Query PostgreSQL for authorized social accounts
        social_accounts = (
            db.query(SocialAccount)
            .filter(SocialAccount.id.in_(target_account_ids))
            .all()
        )
        account_map = {acc.id: acc for acc in social_accounts}

        results_dict: Dict[str, AccountPublishResult] = {}
        any_retryable_failure = False

        for acc_id in target_account_ids:
            social_account = account_map.get(acc_id)
            if not social_account:
                logger.error(f"SocialAccount {acc_id} not found in database for post {post_id}.")
                results_dict[str(acc_id)] = AccountPublishResult(
                    account_id=acc_id,
                    platform=SocialPlatform.TWITTER,  # Fallback for missing
                    status=PublishResultStatus.FAILED,
                    error_code="ACCOUNT_NOT_FOUND",
                    error_message="Target social account was not found in PostgreSQL.",
                    retryable=False
                )
                continue

            if social_account.connection_status != SocialAccountStatus.CONNECTED:
                logger.warning(f"SocialAccount {acc_id} is disconnected ({social_account.connection_status.value}).")
                results_dict[str(acc_id)] = AccountPublishResult(
                    account_id=acc_id,
                    platform=social_account.platform,
                    status=PublishResultStatus.FAILED,
                    error_code="ACCOUNT_DISCONNECTED",
                    error_message=f"Social account connection status is '{social_account.connection_status.value}'.",
                    retryable=False
                )
                continue

            # Resolve platform adapter
            try:
                adapter = get_platform_adapter(social_account.platform)
            except Exception as e:
                logger.error(f"Could not resolve platform adapter for {social_account.platform}: {e}")
                results_dict[str(acc_id)] = AccountPublishResult(
                    account_id=acc_id,
                    platform=social_account.platform,
                    status=PublishResultStatus.FAILED,
                    error_code="ADAPTER_NOT_FOUND",
                    error_message=str(e),
                    retryable=False
                )
                continue

            customization = platform_customizations.get(social_account.platform.value)

            # Platform content validation
            val_res = adapter.validate_content(content=content, media=media, customization=customization)
            if not val_res.is_valid:
                logger.warning(f"Post {post_id} validation failed for {social_account.platform.value}: {val_res.errors}")
                results_dict[str(acc_id)] = AccountPublishResult(
                    account_id=acc_id,
                    platform=social_account.platform,
                    status=PublishResultStatus.FAILED,
                    error_code="VALIDATION_ERROR",
                    error_message="; ".join(val_res.errors),
                    retryable=False
                )
                continue

            # Format payload and execute dispatch
            payload = adapter.format_payload(content=content, media=media, customization=customization)
            publish_res = await adapter.publish(social_account=social_account, payload=payload)

            if publish_res.retryable:
                any_retryable_failure = True

            results_dict[str(acc_id)] = AccountPublishResult(
                account_id=acc_id,
                platform=publish_res.platform,
                status=publish_res.status,
                external_post_id=publish_res.external_post_id,
                error_code=publish_res.error_code,
                error_message=publish_res.error_message,
                retryable=publish_res.retryable,
                published_at=publish_res.published_at
            )

        # 4. Record publishing results in MongoDB and update state machine
        updated_post = await PostService.record_publish_results(
            mongo_db=mongo_db,
            post_id=post_id,
            new_results=results_dict
        )

        return {
            "post_id": post_id,
            "final_status": updated_post.get("status") if updated_post else "UNKNOWN",
            "results_count": len(results_dict),
            "any_retryable": any_retryable_failure
        }

    finally:
        db.close()


class PublishingTask(Task):
    """Custom task wrapper providing automatic retry and error tracking."""
    autoretry_for = ()
    max_retries = 3
    retry_backoff = True
    retry_jitter = True


@celery_app.task(bind=True, base=PublishingTask, name="app.tasks.publishing.publish_post_task")
def publish_post_task(self, post_id: str, account_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Celery background worker task for multi-platform post publishing.
    Executes synchronously within the Celery worker process by wrapping the async workflow.
    """
    logger.info(f"[Celery Worker] Starting publish_post_task for post_id: {post_id}")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # If running in an active loop (e.g. in testing)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(asyncio.run, _async_publish_post_execution(post_id, account_ids)).result()
    else:
        result = loop.run_until_complete(_async_publish_post_execution(post_id, account_ids))

    logger.info(f"[Celery Worker] Finished publish_post_task for post_id: {post_id}. Result: {result}")
    return result


@celery_app.task(name="app.tasks.publishing.cancel_scheduled_task")
def cancel_scheduled_task(task_id: str) -> Dict[str, Any]:
    """Revoke a scheduled Celery task by ID."""
    logger.info(f"[Celery Worker] Revoking task: {task_id}")
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "status": "REVOKED"}
