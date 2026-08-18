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
    try:
        validate_production_configuration(settings)
    except Exception as exc:
        logger.critical(f"Production configuration warning on boot: {exc}")
        from app.core.safety_controller import safety_controller
        await safety_controller.enable_safe_mode("STREAM_A", reason=f"Config issue: {exc}")

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

    # 10. Autonomous Health Supervisor
    from app.services.operations.health_supervisor import health_supervisor
    await health_supervisor.start()

    # 11. Mark Ready
    logger.info(f"{settings.app_name} is READY to accept traffic.")

    yield

    # Shutdown Sequence
    logger.info(f"Initiating graceful shutdown of {settings.app_name}...")

    # 1. Mark Safety Controller as SHUTTING_DOWN
    try:
        from app.core.safety_controller import safety_controller
        await safety_controller.enter_shutting_down()
    except Exception as exc:
        logger.warning(f"Error updating safety state during shutdown: {exc}")

    # 2. Stop Health Supervisor
    try:
        await health_supervisor.stop()
    except Exception as exc:
        logger.warning(f"Error stopping health supervisor: {exc}")

    # 3. Stop Stream Supervisors
    try:
        from app.services.youtube.stream_supervisor import stream_supervisor
        await stream_supervisor.shutdown()
    except Exception as exc:
        logger.warning(f"Error shutting down stream supervisor: {exc}")

    # 4. Stop Modules
    try:
        await module_manager.stop_all()
    except Exception as exc:
        logger.warning(f"Error stopping modules during shutdown: {exc}")

    # 5. Stop Gemini Queue
    try:
        from app.services.gemini import gemini_manager
        await gemini_manager.shutdown()
    except Exception as exc:
        logger.warning(f"Error shutting down Gemini manager: {exc}")

    # 6. Close Redis Connection
    try:
        await redis_state.close()
    except Exception as exc:
        logger.warning(f"Error closing Redis: {exc}")

    # 7. Close Database Connection
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


from fastapi.responses import FileResponse
from fastapi import Request

@app.get("/", tags=["Root"])
async def root(request: Request):
    """Root endpoint welcoming the caller or serving Next.js frontend."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    accept = request.headers.get("accept", "")
    if os.path.exists(index_path) and ("text/html" in accept or "*/*" in accept):
        return FileResponse(index_path)
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs": "/docs",
        "health": "/api/v1/health",
        "liveness": "/api/v1/health/live",
        "readiness": "/api/v1/health/ready",
    }


@app.get("/health/live", tags=["Health"])
@app.get("/health", tags=["Health"])
async def root_health_live():
    """Root-level liveness probe alias for Railway default healthcheck configurations."""
    return {
        "status": "LIVE",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health/ready", tags=["Health"])
async def root_health_ready():
    """Root-level readiness probe alias."""
    from app.db.session import ping_database
    from app.core.redis import redis_state
    db_health = await ping_database()
    redis_health = await redis_state.ping()
    is_db_ok = db_health["status"] in ["HEALTHY", "NOT_CONFIGURED"]
    return {
        "status": "READY" if is_db_ok else "NOT_READY",
        "database": db_health["status"],
        "redis": redis_health["status"],
    }


# Mount static frontend dashboard if available
import os
from fastapi.staticfiles import StaticFiles

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static_frontend")

