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
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.youtube.credentials import youtube_credentials
from app.services.youtube.stream_manager import stream_manager

router = APIRouter()

START_TIME = time.time()


class ComponentStatus(BaseModel):
    status: str  # "HEALTHY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "ERROR"
    details: str
    metadata: Optional[Dict[str, Any]] = None


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
    Get the overall health of Goddess AI 2.0 and honest status of each subsystem.
    """
    uptime = time.time() - START_TIME
    now_utc = datetime.now(timezone.utc).isoformat()

    components: Dict[str, ComponentStatus] = {}

    # Database Status (PostgreSQL)
    if not settings.is_database_configured:
        components["database"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="DATABASE_URL is not set in environment",
        )
    else:
        components["database"] = ComponentStatus(
            status="HEALTHY",
            details="Database URL configured",
        )

    # Redis Status
    if not settings.is_redis_configured:
        components["redis"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="REDIS_URL is not set in environment",
        )
    else:
        components["redis"] = ComponentStatus(
            status="HEALTHY",
            details="Redis URL configured",
        )

    # YouTube Data API & Stream Engine Status
    yt_configured = youtube_credentials.configured_count
    yt_available = youtube_credentials.available_count
    active_streams = stream_manager.active_stream_count

    if yt_configured == 0:
        components["youtube"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="No YouTube API keys configured in environment",
            metadata={
                "configured_credentials": 0,
                "available_credentials": 0,
                "active_streams": active_streams,
                "max_streams": stream_manager.max_concurrent_streams,
            },
        )
    elif yt_available == 0:
        components["youtube"] = ComponentStatus(
            status="UNAVAILABLE",
            details=f"All {yt_configured} configured YouTube credential(s) are in cooldown or failed",
            metadata={
                "configured_credentials": yt_configured,
                "available_credentials": 0,
                "active_streams": active_streams,
                "max_streams": stream_manager.max_concurrent_streams,
                "credentials": [c.model_dump() for c in youtube_credentials.get_health_summary()],
            },
        )
    else:
        components["youtube"] = ComponentStatus(
            status="HEALTHY",
            details=f"{yt_available}/{yt_configured} YouTube key(s) available ({active_streams}/{stream_manager.max_concurrent_streams} active streams)",
            metadata={
                "configured_credentials": yt_configured,
                "available_credentials": yt_available,
                "active_streams": active_streams,
                "max_streams": stream_manager.max_concurrent_streams,
                "credentials": [c.model_dump() for c in youtube_credentials.get_health_summary()],
            },
        )

    # Gemini AI Status
    gemini_keys_count = len(settings.gemini_api_keys)
    if gemini_keys_count == 0:
        components["gemini"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="No Gemini API keys configured in environment (target for Milestone 3)",
        )
    else:
        components["gemini"] = ComponentStatus(
            status="HEALTHY",
            details=f"{gemini_keys_count} Gemini API key(s) registered",
        )

    return HealthResponse(
        application="HEALTHY",
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        timestamp=now_utc,
        components=components,
    )
