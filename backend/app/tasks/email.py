import logging
from typing import Dict, Any
from datetime import datetime, timezone
from celery import Task
from app.core.celery_app import celery_app
from app.db.postgres import SessionLocal
from app.models.team_invitation import TeamInvitation
from app.models.enums import TeamInvitationStatus
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class EmailTask(Task):
    """Custom task wrapper providing automatic retry for transient mail delivery issues."""
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_jitter = True


@celery_app.task(bind=True, base=EmailTask, name="app.tasks.email.send_invitation_email_task")
def send_invitation_email_task(self, invitation_id: int, invite_url: str) -> Dict[str, Any]:
    """
    Celery background worker task for delivering invitation emails.
    """
    logger.info(f"[Celery Worker] Starting send_invitation_email_task for invitation_id: {invitation_id}")
    db = SessionLocal()
    try:
        # 1. Fetch invitation
        inv = db.query(TeamInvitation).filter_by(id=invitation_id).first()
        if not inv:
            logger.error(f"TeamInvitation {invitation_id} not found in database.")
            return {"invitation_id": invitation_id, "status": "ERROR_NOT_FOUND"}

        # 2. Check if active/pending
        if inv.status != TeamInvitationStatus.PENDING:
            logger.warning(f"Invitation {invitation_id} is not pending (status: {inv.status.value}). Skipping email.")
            return {"invitation_id": invitation_id, "status": f"SKIPPED_STATUS_{inv.status.value}"}

        # 3. Check if expired
        # Ensure comparison is timezone-aware
        now = datetime.now(timezone.utc)
        expires_at = inv.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            logger.warning(f"Invitation {invitation_id} has expired. Skipping email.")
            return {"invitation_id": invitation_id, "status": "SKIPPED_EXPIRED"}

        # 4. Resolve details for email
        inviter_name = inv.invited_by.full_name or inv.invited_by.email
        team_name = inv.team.name
        recipient_email = inv.email
        role = inv.role.value

        # 5. Dispatch email
        logger.info(f"Delivering invitation email {invitation_id} to recipient email domain: {recipient_email.split('@')[-1]}")
        EmailService.send_invitation_email(
            email=recipient_email,
            team_name=team_name,
            inviter_name=inviter_name,
            role_name=role,
            invite_url=invite_url
        )

        return {"invitation_id": invitation_id, "status": "SENT"}
    except Exception as e:
        logger.error(f"Error executing send_invitation_email_task for invitation_id {invitation_id}: {str(e)}")
        # Raise for Celery autoretry wrapper
        raise e
    finally:
        db.close()
