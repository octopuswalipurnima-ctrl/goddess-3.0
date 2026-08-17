"""
Main Entrypoint for GODDESS AI 2.0 Backend.

Initializes FastAPI application, CORS middleware, lifespan events, and API routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager handling startup and shutdown events."""
    # Startup
    setup_logging(settings.log_level)
    logger.info(f"Starting {settings.app_name} v{settings.app_version} in [{settings.environment}] mode...")
    logger.info(f"CORS origins configured: {settings.cors_origins}")
    logger.info(f"Database configured: {settings.is_database_configured}")
    logger.info(f"Redis configured: {settings.is_redis_configured}")
    logger.info(f"YouTube keys registered: {len(settings.youtube_api_keys)}")
    logger.info(f"Gemini keys registered: {len(settings.gemini_api_keys)}")

    # Start AI, Moderation, Co-Host, and Module subsystems
    from app.services.moderation import moderation_manager
    moderation_manager.start()

    from app.services.cohost import cohost_manager
    cohost_manager.start()

    from app.modules import module_manager
    await module_manager.start_all()

    yield

    # Shutdown
    await module_manager.stop_all()

    from app.services.gemini import gemini_manager
    await gemini_manager.shutdown()
    logger.info(f"Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Asynchronous backend core for multi-stream live moderation and AI co-host.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint welcoming the caller and pointing to documentation."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
