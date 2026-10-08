import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Query, HTTPException, status, Header, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.instagram_data import MetaWebhookEvent, InstagramComment, InstagramMedia
from app.models.social_account import SocialAccount

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/meta", summary="Meta Webhook Verification")
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """
    Handle Meta Webhook verification handshake.
    Responds with hub.challenge if hub.verify_token matches configured secret.
    """
    configured_token = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "socialpilot_meta_webhook_secret")

    if hub_mode == "subscribe" and hub_verify_token == configured_token:
        logger.info("Meta webhook verification challenge succeeded.")
        return PlainTextResponse(content=hub_challenge or "", status_code=200)

    logger.warning(f"Meta webhook verification rejected: mode={hub_mode}, token={hub_verify_token}")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch.")


@router.post("/meta", summary="Receive Meta Webhook Events")
async def receive_meta_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")
):
    """
    Secure Meta Webhook receiver.
    Validates HMAC SHA-256 payload signature, deduplicates events, and stores in PostgreSQL.
    """
    raw_body = await request.body()

    # 1. Signature validation (when Meta Client Secret is configured and header is present)
    client_secret = settings.META_CLIENT_SECRET
    if client_secret and x_hub_signature_256:
        expected_sig = "sha256=" + hmac.new(
            client_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, x_hub_signature_256):
            logger.warning("Meta webhook rejected due to invalid HMAC SHA-256 signature.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature.")

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Malformed JSON in Meta webhook: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    entries = payload.get("entry", [])
    processed_count = 0

    for entry in entries:
        entry_id = str(entry.get("id", ""))
        changes = entry.get("changes", [])

        for change in changes:
            field = change.get("field", "unknown")
            value = change.get("value", {})

            # Generate deterministic hash for event deduplication
            raw_dedup_string = f"{entry_id}:{field}:{value.get('id')}:{value.get('created_time')}:{value.get('text')}"
            event_hash = hashlib.sha256(raw_dedup_string.encode("utf-8")).hexdigest()

            # Deduplication check: do not process duplicate events
            existing = db.query(MetaWebhookEvent).filter(MetaWebhookEvent.event_id == event_hash).first()
            if existing:
                logger.info(f"Deduplicated duplicate webhook event {event_hash}")
                continue

            event_record = MetaWebhookEvent(
                event_id=event_hash,
                field=field,
                account_identifier=entry_id,
                payload=change,
                processed=True
            )
            db.add(event_record)
            processed_count += 1

            # If comment event, update local comment cache if related media exists
            if field == "comments" and isinstance(value, dict):
                comment_id = value.get("id")
                comment_text = value.get("text", "")
                media_data = value.get("media", {})
                media_ext_id = media_data.get("id")

                if media_ext_id and comment_id:
                    media_record = db.query(InstagramMedia).filter(InstagramMedia.external_media_id == str(media_ext_id)).first()
                    if media_record:
                        existing_comment = db.query(InstagramComment).filter(InstagramComment.external_comment_id == str(comment_id)).first()
                        if not existing_comment:
                            new_comment = InstagramComment(
                                media_id=media_record.id,
                                external_comment_id=str(comment_id),
                                from_username=value.get("from", {}).get("username"),
                                from_user_id=value.get("from", {}).get("id"),
                                text=comment_text,
                                like_count=0
                            )
                            db.add(new_comment)
                            media_record.comments_count += 1
                            media_record.engagement += 1

    db.commit()
    logger.info(f"Meta webhook received: {processed_count} events persisted and deduplicated.")
    return {"status": "success", "events_processed": processed_count}
