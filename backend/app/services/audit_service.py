import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password", "hashed_password", "access_token", "refresh_token",
    "token", "secret", "smtp_password", "code", "authorization",
    "cookie", "client_secret", "raw_token"
}


def sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Remove or redact any sensitive credentials, tokens, or secrets from metadata dictionary."""
    if not meta:
        return {}
    sanitized = {}
    for k, v in meta.items():
        if k.lower() in SENSITIVE_KEYS:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_metadata(v)
        else:
            sanitized[k] = v
    return sanitized


def is_mock_db(db: Any) -> bool:
    """Helper to safely check if db is a mock object rather than a Motor AsyncIOMotorDatabase instance."""
    if db is None:
        return False
    return type(db).__name__ != "AsyncIOMotorDatabase"


class AuditService:
    @staticmethod
    async def log_event(
        mongo_db: Optional[AsyncIOMotorDatabase],
        team_id: int,
        action: str,
        entity_type: str,
        description: str,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        entity_id: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record an audit log entry in MongoDB audit_logs collection.
        Enclosed in try...except block to guarantee primary business transactions never fail.
        """
        client_to_close = None
        try:
            if is_mock_db(mongo_db):
                target_db = mongo_db
            else:
                client_to_close = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
                target_db = client_to_close[settings.MONGODB_DB_NAME]

            clean_meta = sanitize_metadata(metadata)
            doc = {
                "team_id": int(team_id),
                "actor_id": int(actor_id) if actor_id is not None else None,
                "actor_name": actor_name or "System",
                "action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id) if entity_id is not None else None,
                "description": description,
                "metadata": clean_meta,
                "created_at": datetime.now(timezone.utc)
            }
            await target_db["audit_logs"].insert_one(doc)
            return True
        except Exception as e:
            logger.warning(f"Audit log recording suppressed failure: {e}")
            return False
        finally:
            if client_to_close is not None:
                try:
                    client_to_close.close()
                except Exception:
                    pass

    @staticmethod
    async def get_team_activity(
        mongo_db: Optional[AsyncIOMotorDatabase],
        team_id: int,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve paginated team activity events sorted newest first.
        """
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20

        skip = (page - 1) * limit
        filter_query = {"team_id": int(team_id)}

        client_to_close = None
        try:
            if is_mock_db(mongo_db):
                target_db = mongo_db
            else:
                client_to_close = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
                target_db = client_to_close[settings.MONGODB_DB_NAME]

            total = await target_db["audit_logs"].count_documents(filter_query)
            cursor = target_db["audit_logs"].find(filter_query).sort("created_at", -1).skip(skip).limit(limit)

            items = []
            async for doc in cursor:
                items.append({
                    "id": str(doc.get("_id")),
                    "team_id": doc.get("team_id"),
                    "actor_id": doc.get("actor_id"),
                    "actor_name": doc.get("actor_name", "System"),
                    "action": doc.get("action"),
                    "entity_type": doc.get("entity_type"),
                    "entity_id": doc.get("entity_id"),
                    "description": doc.get("description"),
                    "metadata": doc.get("metadata", {}),
                    "created_at": doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at"))
                })

            total_pages = math.ceil(total / limit) if total > 0 else 1

            return {
                "items": items,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }
        except Exception as e:
            logger.warning(f"Error fetching team activity: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 1
            }
        finally:
            if client_to_close is not None:
                try:
                    client_to_close.close()
                except Exception:
                    pass
