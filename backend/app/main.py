"""
Main Entrypoint for GODDESS AI 2.0 Backend.

Initializes FastAPI application, security middlewares, deterministic lifespan events,
CORS security, and API routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.auth.middleware import RequestCorrelationMiddleware, SecurityHeadersMiddleware
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import redis_state
from app.db.session import close_db, get_db_session, ping_database

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Deterministic 14-step Application Lifespan Manager:
    Startup:
      1. Load and validate environment configuration.
      2. Verify production security constraints (secret key strength).
      3. Initialize structured logging & secret masking.
      4. Initialize and ping database connection.
      5. Initialize Redis state manager with safe in-memory fallback.
      6. Execute persistent restart recovery pipeline (modules, co-host, settings).
      7. Initialize Module System.
      8. Start Moderation Engine event subscriptions.
      9. Start Co-Host Engine event subscriptions.
      10. Mark system as READY for production traffic.
    Shutdown:
      1. Stop Module workers.
      2. Shutdown Gemini queue workers.
      3. Close Redis connection pool.
      4. Close database connection pool.
      5. Exit cleanly.
    """
    # 1-3. Logging & Configuration
    setup_logging(settings.log_level)
    logger.info(f"Starting {settings.app_name} v{settings.app_version} in [{settings.environment}] mode...")
    
    # 2. Production Security & Configuration Validation
    from app.core.validator import validate_production_configuration
    validate_production_configuration(settings)

    # 4. Database Initialization & Ping
    db_status = await ping_database()
    logger.info(f"Database status: {db_status['status']} ({db_status['details']})")

    # 5. Redis State Manager Initialization
    await redis_state.initialize()
    redis_status = await redis_state.ping()
    logger.info(f"Redis status: {redis_status['status']} (Mode: {redis_status['mode']})")

    # 6. Restart Recovery (if DB is configured)
    if settings.is_database_configured and db_status["status"] == "HEALTHY":
        try:
            from app.db.recovery import RecoveryManager
            async with get_db_session() as session:
                recovery = RecoveryManager(session)
                summary = await recovery.restore_all()
                logger.info(f"Startup Recovery Summary: {summary}")
        except Exception as exc:
            logger.warning(f"Startup recovery failed (non-fatal): {exc}")

    # 7-9. Subsystems Startup
    from app.services.moderation import moderation_manager
    moderation_manager.start()

    from app.services.cohost import cohost_manager
    cohost_manager.start()

    from app.modules import module_manager
    await module_manager.start_all()

    # 10. Mark Ready
    logger.info(f"{settings.app_name} is READY to accept traffic.")

    yield

    # Shutdown Sequence
    logger.info(f"Initiating graceful shutdown of {settings.app_name}...")
    try:
        await module_manager.stop_all()
    except Exception as exc:
        logger.warning(f"Error stopping modules during shutdown: {exc}")

    try:
        from app.services.gemini import gemini_manager
        await gemini_manager.shutdown()
    except Exception as exc:
        logger.warning(f"Error shutting down Gemini manager: {exc}")

    try:
        await redis_state.close()
    except Exception as exc:
        logger.warning(f"Error closing Redis: {exc}")

    try:
        await close_db()
    except Exception as exc:
        logger.warning(f"Error closing Database: {exc}")

    logger.info(f"{settings.app_name} shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Asynchronous backend core for multi-stream live moderation and AI co-host.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request Correlation & Logging Middleware
app.add_middleware(RequestCorrelationMiddleware)

# 3. Production CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
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
        "liveness": "/api/v1/health/live",
        "readiness": "/api/v1/health/ready",
    }
