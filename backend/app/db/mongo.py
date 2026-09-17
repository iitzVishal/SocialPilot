import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)


import asyncio

class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    loop: Optional[asyncio.AbstractEventLoop] = None


mongo_manager = MongoDBManager()


async def connect_to_mongo() -> None:
    """Initialize Async MongoDB Client connection."""
    try:
        current_loop = asyncio.get_running_loop()
        mongo_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000
        )
        mongo_manager.db = mongo_manager.client[settings.MONGODB_DB_NAME]
        mongo_manager.loop = current_loop
        logger.info("Connected to MongoDB successfully.")
    except Exception as e:
        logger.warning(f"MongoDB connection attempt deferred or failed: {e}")


async def close_mongo_connection() -> None:
    """Close Async MongoDB Client connection."""
    if mongo_manager.client is not None:
        mongo_manager.client.close()
        mongo_manager.client = None
        mongo_manager.db = None
        mongo_manager.loop = None
        logger.info("Closed MongoDB connection.")


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Dependency helper to access the MongoDB database instance."""
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if mongo_manager.client is None or (current_loop is not None and (mongo_manager.loop is not current_loop or getattr(mongo_manager.loop, "_closed", False))):
        if mongo_manager.client is not None:
            try:
                mongo_manager.client.close()
            except Exception:
                pass
        try:
            mongo_manager.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=2000
            )
            mongo_manager.db = mongo_manager.client[settings.MONGODB_DB_NAME]
            mongo_manager.loop = current_loop
        except Exception as e:
            logger.warning(f"MongoDB client initialization failed: {e}")
            return None
    return mongo_manager.db


def ensure_active_mongo_db(db: Optional[AsyncIOMotorDatabase] = None) -> AsyncIOMotorDatabase:
    """Ensure the returned MongoDB database instance is bound to the currently running event loop."""
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if db is None:
        return get_mongo_db()

    # Skip mock objects
    if type(db).__name__ != "AsyncIOMotorDatabase":
        return db

    try:
        client = getattr(db, "client", None)
        client_loop = getattr(client, "io_loop", None) or getattr(client, "_io_loop", None)
        if client_loop is not None and (client_loop is not current_loop or getattr(client_loop, "_closed", False)):
            return get_mongo_db()
    except Exception:
        return get_mongo_db()

    return db
