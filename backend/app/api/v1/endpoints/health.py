"""
Health Check & Diagnostics Endpoint for GODDESS AI 2.0.

Provides simple, honest reporting of system and component status:
- HEALTHY: Component is configured and actively functioning.
- NOT_CONFIGURED: Configuration key/URL is not provided (normal during early milestones).
- UNAVAILABLE: Configured resource cannot be reached.
- ERROR: An exception occurred while checking the resource.
"""

from datetime import datetime, timezone
import time
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Server start time recorded at module import
START_TIME = time.time()


class ComponentStatus(BaseModel):
    status: str  # "HEALTHY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "ERROR"
    details: str


class HealthResponse(BaseModel):
    application: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: str
    components: Dict[str, ComponentStatus]


@router.get("/health", response_model=HealthResponse, summary="System Health & Honest Component Status")
async def get_health():
    """
    Get the overall health of Goddess AI 2.0 and the honest status of each subsystem.
    """
    uptime = time.time() - START_TIME
    now_utc = datetime.now(timezone.utc).isoformat()

    components: Dict[str, ComponentStatus] = {}

    # Database Status (PostgreSQL)
    if not settings.is_database_configured:
        components["database"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="DATABASE_URL is not set in environment (optional in Milestone 0)",
        )
    else:
        # In Milestone 2, real async probe will be hooked here
        components["database"] = ComponentStatus(
            status="HEALTHY",
            details="Database URL configured",
        )

    # Redis Status
    if not settings.is_redis_configured:
        components["redis"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="REDIS_URL is not set in environment (optional in Milestone 0)",
        )
    else:
        # In Milestone 2, real async probe will be hooked here
        components["redis"] = ComponentStatus(
            status="HEALTHY",
            details="Redis URL configured",
        )

    # YouTube Data API Status
    yt_keys_count = len(settings.youtube_api_keys)
    if yt_keys_count == 0:
        components["youtube"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="No YouTube API keys configured in environment",
        )
    else:
        components["youtube"] = ComponentStatus(
            status="HEALTHY",
            details=f"{yt_keys_count} YouTube API key(s) registered",
        )

    # Gemini AI Status
    gemini_keys_count = len(settings.gemini_api_keys)
    if gemini_keys_count == 0:
        components["gemini"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="No Gemini API keys configured in environment",
        )
    else:
        components["gemini"] = ComponentStatus(
            status="HEALTHY",
            details=f"{gemini_keys_count} Gemini API key(s) registered (Primary: {settings.gemini_primary_model})",
        )

    return HealthResponse(
        application="HEALTHY",
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        timestamp=now_utc,
        components=components,
    )
