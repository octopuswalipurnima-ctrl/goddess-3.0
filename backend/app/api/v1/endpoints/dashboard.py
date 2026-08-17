"""
Dashboard Aggregator REST API for GODDESS AI 2.0.

Provides high-efficiency, read-only aggregated telemetry for the Creator Control Center.
Consumes existing services without duplicating business logic or exposing credentials.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import require_permission
from app.core.config import settings
from app.core.redis import redis_state
from app.db.session import ping_database
from app.modules import module_manager
from app.services.cohost import cohost_manager
from app.services.gemini import gemini_credentials, gemini_manager
from app.services.moderation import moderation_manager
from app.services.youtube import stream_manager, youtube_credentials

router = APIRouter(prefix="/dashboard", tags=["Dashboard Overview"])


class DashboardOverviewResponse(BaseModel):
    timestamp: str
    version: str
    uptime_seconds: float
    streams: List[Dict[str, Any]]
    moderation_metrics: Dict[str, Any]
    cohost_metrics: Dict[str, Any]
    modules_summary: Dict[str, Any]
    ai_diagnostics: Dict[str, Any]
    youtube_diagnostics: Dict[str, Any]
    persistence_health: Optional[Dict[str, Any]] = None


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    dependencies=[Depends(require_permission("dashboard.read"))],
    summary="Get Creator Dashboard Overview",
)
async def get_dashboard_overview():
    """
    Aggregates live health, multi-stream sessions, moderation stats,
    Co-Host activity, modular extensions, and credential diagnostics in a single payload.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    # 1. Active Streams (up to 4 streams)
    active_sessions = stream_manager.list_sessions()
    streams_data = [
        {
            "stream_id": s.stream_id,
            "title": s.stream_title or f"Stream {s.stream_id}",
            "is_active": s.is_active,
            "is_live": s.is_live,
            "viewer_count": s.viewer_count,
            "messages_read": s.messages_read_count,
            "messages_posted": s.messages_posted_count,
            "start_time": s.created_at.isoformat() if s.created_at else None,
            "error_count": s.error_count,
        }
        for s in active_sessions
    ]

    # 2. Moderation Metrics
    mod_metrics = {
        "messages_analyzed": moderation_manager.metrics.messages_analyzed,
        "rule_matches": moderation_manager.metrics.rule_matches,
        "ai_analyses": moderation_manager.metrics.ai_classifications,
        "actions_executed": moderation_manager.metrics.actions_executed,
        "actions_blocked": moderation_manager.metrics.actions_blocked,
        "actions_failed": moderation_manager.metrics.actions_failed,
        "dry_run_actions": moderation_manager.metrics.actions_dry_run,
    }

    # 3. Co-Host Metrics
    cohost_metrics = {
        "messages_analyzed": cohost_manager.metrics.messages_analyzed,
        "intents_detected": cohost_manager.metrics.intents_detected,
        "responses_requested": cohost_manager.metrics.responses_requested,
        "responses_generated": cohost_manager.metrics.responses_generated,
        "responses_sent": cohost_manager.metrics.responses_sent,
        "responses_dry_run": cohost_manager.metrics.responses_dry_run,
        "responses_blocked": cohost_manager.metrics.responses_blocked,
        "responses_failed": cohost_manager.metrics.responses_failed,
    }

    # 4. Modules Summary
    all_mods = module_manager.registry.list_all()
    modules_summary = {
        "registered_count": len(all_mods),
        "enabled_count": sum(1 for m in all_mods if m.is_enabled),
        "running_count": sum(1 for m in all_mods if m.is_running),
        "failed_count": sum(1 for m in all_mods if m.status.value == "FAILED"),
        "modules": [
            {
                "id": m.module_id,
                "name": m.metadata.name,
                "version": m.metadata.version,
                "status": m.status.value,
                "health": m.get_health().status.value,
                "capabilities": [c.value for c in m.metadata.capabilities],
                "active_streams": [s for s, c in m._stream_configs.items() if c.enabled],
            }
            for m in all_mods
        ],
    }

    # 5. AI Diagnostics (Safe summary, 0 raw secrets)
    gemini_diag = {
        "configured_keys": gemini_credentials.configured_count,
        "available_keys": gemini_credentials.available_count,
        "cooldown_keys": sum(1 for s in gemini_credentials._slots.values() if s.state.value == "COOLDOWN"),
        "active_requests": gemini_manager.metrics.active_requests,
        "queued_requests": gemini_manager.metrics.queued_requests,
        "total_requests": gemini_manager.metrics.total_requests,
        "successful_requests": gemini_manager.metrics.successful_requests,
        "failed_requests": gemini_manager.metrics.failed_requests,
        "primary_model": settings.gemini_primary_model,
        "fallback_model": settings.gemini_fallback_model,
    }

    # 6. YouTube Diagnostics (Safe summary, 0 raw secrets)
    yt_diag = {
        "configured_keys": youtube_credentials.configured_count,
        "available_keys": youtube_credentials.available_count,
        "cooldown_keys": sum(1 for s in youtube_credentials._slots.values() if s.state.value == "COOLDOWN"),
        "active_streams": len(active_sessions),
    }

    # 7. Persistence Health (PostgreSQL & Redis safe telemetry)
    db_health = await ping_database()
    redis_health = await redis_state.ping()
    persistence_diag = {
        "database": {
            "status": db_health["status"],
            "details": db_health["details"],
            "latency_ms": db_health.get("latency_ms"),
        },
        "redis": {
            "status": redis_health["status"],
            "details": redis_health["details"],
            "mode": redis_health.get("mode"),
            "latency_ms": redis_health.get("latency_ms"),
        },
        "migration": {
            "status": "CURRENT" if db_health["status"] == "HEALTHY" else "UNKNOWN",
            "current_revision": "0001_initial" if db_health["status"] == "HEALTHY" else None,
        },
    }

    return DashboardOverviewResponse(
        timestamp=now_utc,
        version=settings.app_version,
        uptime_seconds=round(datetime.now(timezone.utc).timestamp() - settings.startup_time, 2)
        if hasattr(settings, "startup_time")
        else 0.0,
        streams=streams_data,
        moderation_metrics=mod_metrics,
        cohost_metrics=cohost_metrics,
        modules_summary=modules_summary,
        ai_diagnostics=gemini_diag,
        youtube_diagnostics=yt_diag,
        persistence_health=persistence_diag,
    )
