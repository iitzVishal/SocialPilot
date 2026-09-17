from fastapi import APIRouter
from sqlalchemy import text
from app.core.config import settings
from app.db.postgres import SessionLocal
from app.db.mongo import get_mongo_db
from app.db.redis import get_redis_client

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Service health check endpoint.
    Reports operational status and connectivity indicators for PostgreSQL, MongoDB, and Redis.
    """
    # 1. Check PostgreSQL
    pg_status = "unreachable"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        pg_status = "connected"
    except Exception as e:
        pg_status = f"disconnected ({type(e).__name__})"

    # 2. Check MongoDB
    mongo_status = "unreachable"
    try:
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            await mongo_db.command("ping")
            mongo_status = "connected"
        else:
            mongo_status = "not initialized"
    except Exception as e:
        mongo_status = f"disconnected ({type(e).__name__})"

    # 3. Check Redis
    redis_status = "unreachable"
    try:
        redis_client = get_redis_client()
        if redis_client is not None:
            await redis_client.ping()
            redis_status = "connected"
        else:
            redis_status = "not initialized"
    except Exception as e:
        redis_status = f"disconnected ({type(e).__name__})"

    return {
        "status": "healthy" if (pg_status == "connected" and mongo_status == "connected" and redis_status == "connected") else "degraded",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "api": "healthy",
            "postgresql": "healthy" if pg_status == "connected" else pg_status,
            "mongodb": "healthy" if mongo_status == "connected" else mongo_status,
            "redis": "healthy" if redis_status == "connected" else redis_status,
        },
        "databases": {
            "postgresql": pg_status,
            "mongodb": mongo_status,
            "redis": redis_status,
        },
        "oauth_configuration": {
            "frontend_origin": settings.FRONTEND_URL,
            "google_client_id_configured": "YES" if bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID.strip()) else "NO",
            "google_client_id_suffix": settings.GOOGLE_CLIENT_ID.strip()[-6:] if (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID.strip()) else "NONE",
            "meta_client_id_configured": "YES" if bool(settings.META_CLIENT_ID and settings.META_CLIENT_ID.strip()) else "NO",
            "meta_client_secret_configured": "YES" if bool(settings.META_CLIENT_SECRET and settings.META_CLIENT_SECRET.strip()) else "NO",
            "meta_redirect_uri_configured": "YES" if bool(settings.META_REDIRECT_URI and settings.META_REDIRECT_URI.strip()) else "NO",
            "instagram_redirect_uri_configured": "YES" if bool(settings.INSTAGRAM_REDIRECT_URI and settings.INSTAGRAM_REDIRECT_URI.strip()) else "NO",
        }
    }


