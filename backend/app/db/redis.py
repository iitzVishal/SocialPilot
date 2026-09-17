import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


import asyncio

class RedisManager:
    client: Optional[aioredis.Redis] = None
    loop: Optional[asyncio.AbstractEventLoop] = None


redis_manager = RedisManager()


async def connect_to_redis() -> None:
    """Initialize Async Redis client connection."""
    try:
        current_loop = asyncio.get_running_loop()
        redis_manager.client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2
        )
        redis_manager.loop = current_loop
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Redis connection attempt deferred or failed: {e}")


async def close_redis_connection() -> None:
    """Close Async Redis client connection."""
    if redis_manager.client is not None:
        await redis_manager.client.aclose()
        redis_manager.client = None
        redis_manager.loop = None
        logger.info("Closed Redis connection.")


def get_redis_client() -> aioredis.Redis:
    """Dependency helper to access Redis client instance."""
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if redis_manager.client is None or (current_loop is not None and redis_manager.loop != current_loop):
        redis_manager.client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2
        )
        redis_manager.loop = current_loop
    return redis_manager.client
