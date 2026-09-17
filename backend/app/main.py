import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api_router import api_router
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.db.redis import connect_to_redis, close_redis_connection

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("socialpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes and cleans up connections for MongoDB, Redis, and services.
    """
    logger.info("Starting up SocialPilot API...")
    # Initialize document and cache store connections
    await connect_to_mongo()
    await connect_to_redis()
    yield
    logger.info("Shutting down SocialPilot API...")
    await close_mongo_connection()
    await close_redis_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
    description="SocialPilot: Centralized Social Media Scheduler & Campaign Management Platform API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount local media static files route
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles

media_dir = Path(settings.MEDIA_UPLOAD_DIR).resolve()
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/media", StaticFiles(directory=str(media_dir)), name="media")

# Also expose /health at root level for load balancer / container health checks
from app.api.v1.health import health_check
from fastapi.responses import RedirectResponse
app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])


@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect /docs to versioned API documentation."""
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing platform metadata and documentation endpoints."""
    return {
        "title": settings.PROJECT_NAME,
        "status": "online",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
