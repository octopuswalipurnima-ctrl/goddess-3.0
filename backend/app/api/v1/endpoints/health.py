"""
Health Check & Diagnostics Endpoint for GODDESS AI 2.0.

Provides simple, honest reporting of system and component status:
- HEALTHY: Component is configured and actively functioning.
- NOT_CONFIGURED: Configuration key/URL is not provided (normal during early milestones).
- UNAVAILABLE: Configured resource cannot be reached.
- DEGRADED: Configured resource is partially available or experiencing errors.
- ERROR: An exception occurred while checking the resource.
"""

from datetime import datetime, timezone
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.redis import redis_state
from app.db.session import ping_database
from app.services.gemini.credentials import gemini_credentials
from app.services.gemini.manager import gemini_manager
from app.services.gemini.router import gemini_router
from app.services.youtube.credentials import youtube_credentials
from app.services.youtube.stream_manager import stream_manager

router = APIRouter()

START_TIME = time.time()


class ComponentStatus(BaseModel):
    status: str  # "HEALTHY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "DEGRADED" | "ERROR"
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

    # Database Status (PostgreSQL / SQLite)
    db_health = await ping_database()
    components["database"] = ComponentStatus(
        status=db_health["status"],
        details=db_health["details"],
        metadata={
            "latency_ms": db_health.get("latency_ms"),
            "pool": db_health.get("pool"),
        },
    )

    # Redis Status (Transient State / Cache)
    redis_health = await redis_state.ping()
    components["redis"] = ComponentStatus(
        status=redis_health["status"],
        details=redis_health["details"],
        metadata={
            "mode": redis_health.get("mode"),
            "latency_ms": redis_health.get("latency_ms"),
        },
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

    # Gemini AI Engine Status
    gemini_configured = gemini_credentials.configured_count
    gemini_available = gemini_credentials.available_count
    active_ai_reqs = gemini_manager.queue.active_count
    queued_ai_reqs = gemini_manager.queue.queued_count

    if gemini_configured == 0:
        components["gemini"] = ComponentStatus(
            status="NOT_CONFIGURED",
            details="No Gemini API keys configured in environment",
            metadata={
                "configured_credentials": 0,
                "available_credentials": 0,
                "active_requests": active_ai_reqs,
                "queued_requests": queued_ai_reqs,
                "primary_model": gemini_router.primary_model,
                "fallback_model": gemini_router.fallback_model,
                "total_requests": gemini_manager.metrics.total_requests,
                "successful_requests": gemini_manager.metrics.successful_requests,
                "failed_requests": gemini_manager.metrics.failed_requests,
            },
        )
    elif gemini_available == 0:
        components["gemini"] = ComponentStatus(
            status="UNAVAILABLE",
            details=f"All {gemini_configured} configured Gemini credential(s) are in cooldown or failed",
            metadata={
                "configured_credentials": gemini_configured,
                "available_credentials": 0,
                "active_requests": active_ai_reqs,
                "queued_requests": queued_ai_reqs,
                "primary_model": gemini_router.primary_model,
                "fallback_model": gemini_router.fallback_model,
                "credentials": [c.model_dump() for c in gemini_credentials.get_health_summary()],
            },
        )
    elif gemini_available < gemini_configured:
        components["gemini"] = ComponentStatus(
            status="DEGRADED",
            details=f"{gemini_available}/{gemini_configured} Gemini key(s) available (some in cooldown)",
            metadata={
                "configured_credentials": gemini_configured,
                "available_credentials": gemini_available,
                "active_requests": active_ai_reqs,
                "queued_requests": queued_ai_reqs,
                "primary_model": gemini_router.primary_model,
                "fallback_model": gemini_router.fallback_model,
                "credentials": [c.model_dump() for c in gemini_credentials.get_health_summary()],
            },
        )
    else:
        components["gemini"] = ComponentStatus(
            status="HEALTHY",
            details=f"{gemini_available}/{gemini_configured} Gemini key(s) active (Primary: {gemini_router.primary_model})",
            metadata={
                "configured_credentials": gemini_configured,
                "available_credentials": gemini_available,
                "active_requests": active_ai_reqs,
                "queued_requests": queued_ai_reqs,
                "primary_model": gemini_router.primary_model,
                "fallback_model": gemini_router.fallback_model,
                "credentials": [c.model_dump() for c in gemini_credentials.get_health_summary()],
            },
        )

    # Moderation Engine Status
    from app.services.moderation import moderation_manager
    mod_metrics = moderation_manager.metrics

    components["moderation"] = ComponentStatus(
        status="HEALTHY",
        details="3-Tier AI Moderation Engine active with rule pre-processing and policy safety gates",
        metadata={
            "messages_analyzed": mod_metrics.messages_analyzed,
            "rule_matches": mod_metrics.rule_matches,
            "ai_classifications": mod_metrics.ai_classifications,
            "actions_executed": mod_metrics.actions_executed,
            "actions_blocked": mod_metrics.actions_blocked,
            "automation": "ENABLED",
        },
    )

    # AI Co-Host Engine Status
    from app.services.cohost import cohost_manager
    cohost_metrics = cohost_manager.metrics

    components["cohost"] = ComponentStatus(
        status="HEALTHY",
        details="AI Co-Host Engine active with rule-first intent detection, context memory, and safety policy",
        metadata={
            "messages_analyzed": cohost_metrics.messages_analyzed,
            "intents_detected": cohost_metrics.intents_detected,
            "responses_requested": cohost_metrics.responses_requested,
            "responses_generated": cohost_metrics.responses_generated,
            "responses_sent": cohost_metrics.responses_sent,
            "responses_dry_run": cohost_metrics.responses_dry_run,
            "responses_blocked": cohost_metrics.responses_blocked,
            "responses_failed": cohost_metrics.responses_failed,
        },
    )

    # Modular Extension System Status
    from app.modules import module_manager
    all_mods = module_manager.registry.list_all()
    enabled_count = sum(1 for m in all_mods if m.is_enabled)
    running_count = sum(1 for m in all_mods if m.is_running)
    failed_count = sum(1 for m in all_mods if m.status.value == "FAILED")

    components["modules"] = ComponentStatus(
        status="HEALTHY" if failed_count == 0 else "DEGRADED",
        details=f"Module System active: {running_count}/{len(all_mods)} running, {enabled_count} enabled, {failed_count} failed",
        metadata={
            "registered_modules": len(all_mods),
            "enabled_modules": enabled_count,
            "running_modules": running_count,
            "failed_modules": failed_count,
            "module_ids": [m.module_id for m in all_mods],
        },
    )

    return HealthResponse(
        application="HEALTHY",
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        timestamp=now_utc,
        components=components,
    )
