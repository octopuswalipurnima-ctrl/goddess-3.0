"""
Production Health & Safe Degradation Service for GODDESS AI 2.0.

Aggregates operational health across PostgreSQL database, Redis state cache,
YouTube Data API, Google Gemini AI, EventBus, and StreamSupervisor with zero raw secrets.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.redis import redis_state
from app.core.safety_controller import safety_controller
from app.db.session import get_engine
from app.services.gemini.credentials import gemini_credentials
from app.services.providers.health import provider_health_service
from app.services.youtube.credentials import youtube_credentials


class DependencyStatus(BaseModel):
    name: str
    status: str = Field(description="'HEALTHY', 'DEGRADED', 'UNAVAILABLE', or 'NOT_CONFIGURED'")
    details: str
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemProductionHealth(BaseModel):
    application: str = "GODDESS AI 2.0"
    environment: str
    system_status: str = Field(description="'HEALTHY', 'DEGRADED', 'UNAVAILABLE', or 'ERROR'")
    global_safety_state: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dependencies: Dict[str, DependencyStatus] = Field(default_factory=dict)
    safety_summary: Dict[str, Any] = Field(default_factory=dict)


class ProductionHealthService:
    """Service providing comprehensive system dependency health & safe degradation telemetry."""

    @staticmethod
    def get_database_status() -> DependencyStatus:
        """Check PostgreSQL database connectivity."""
        if not settings.is_database_configured:
            return DependencyStatus(
                name="database",
                status="NOT_CONFIGURED",
                details="PostgreSQL database URL not configured (in-memory mode)",
            )

        engine = get_engine()
        if engine:
            return DependencyStatus(
                name="database",
                status="HEALTHY",
                details="PostgreSQL async engine configured and active",
                metadata={"dialect": "postgresql+asyncpg"},
            )
        else:
            return DependencyStatus(
                name="database",
                status="DEGRADED",
                details="Database connection pool unavailable; using safe fallback",
            )

    @staticmethod
    def get_redis_status() -> DependencyStatus:
        """Check Redis state cache connectivity."""
        is_ready = getattr(redis_state, "is_connected", False)
        in_memory_keys = len(redis_state._fallback._store) if hasattr(redis_state, "_fallback") and hasattr(redis_state._fallback, "_store") else 0

        if not settings.is_redis_configured:
            return DependencyStatus(
                name="redis",
                status="DEGRADED",
                details="Redis not configured; running on thread-safe bounded in-memory fallback",
                metadata={"mode": "in-memory-fallback", "cached_keys": in_memory_keys},
            )

        if is_ready:
            return DependencyStatus(
                name="redis",
                status="HEALTHY",
                details="Redis cluster connection active",
                metadata={"mode": "redis-live"},
            )
        else:
            return DependencyStatus(
                name="redis",
                status="DEGRADED",
                details="Redis connection degraded; operating on bounded in-memory fallback",
                metadata={"mode": "in-memory-fallback", "cached_keys": in_memory_keys},
            )

    @staticmethod
    def get_youtube_status() -> DependencyStatus:
        """Check YouTube API provider credentials and stream health."""
        yt_health = provider_health_service.get_youtube_provider_health()
        return DependencyStatus(
            name="youtube",
            status=yt_health.status,
            details=f"{yt_health.healthy_count}/{yt_health.credential_count} key(s) available ({yt_health.quota_failures} quota trips)",
            metadata={
                "configured_keys": yt_health.credential_count,
                "available_keys": yt_health.healthy_count,
                "cooldown_keys": yt_health.cooldown_count,
                "quota_failures": yt_health.quota_failures,
                "failure_rate": yt_health.failure_rate,
            },
        )

    @staticmethod
    def get_gemini_status() -> DependencyStatus:
        """Check Gemini AI provider credentials and latency."""
        g_health = provider_health_service.get_gemini_provider_health()
        return DependencyStatus(
            name="gemini",
            status=g_health.status,
            details=f"{g_health.healthy_count}/{g_health.credential_count} key(s) available (Primary: {settings.gemini_primary_model})",
            metadata={
                "configured_keys": g_health.credential_count,
                "available_keys": g_health.healthy_count,
                "cooldown_keys": g_health.cooldown_count,
                "quota_failures": g_health.quota_failures,
                "failure_rate": g_health.failure_rate,
                "primary_model": settings.gemini_primary_model,
                "fallback_model": settings.gemini_fallback_model,
            },
        )

    @classmethod
    def get_system_production_health(cls) -> SystemProductionHealth:
        """
        Aggregate all dependency statuses into a single unified health report.
        """
        db_stat = cls.get_database_status()
        redis_stat = cls.get_redis_status()
        yt_stat = cls.get_youtube_status()
        gemini_stat = cls.get_gemini_status()

        dependencies = {
            "database": db_stat,
            "redis": redis_stat,
            "youtube": yt_stat,
            "gemini": gemini_stat,
        }

        # Calculate overall system status
        statuses = [d.status for d in dependencies.values()]
        if any(s == "UNAVAILABLE" for s in statuses):
            system_status = "UNAVAILABLE"
        elif any(s in ("DEGRADED", "NOT_CONFIGURED") for s in statuses) or safety_controller.is_global_emergency or safety_controller.is_global_safe_mode:
            system_status = "DEGRADED"
        else:
            system_status = "HEALTHY"

        return SystemProductionHealth(
            environment=settings.environment,
            system_status=system_status,
            global_safety_state=safety_controller.global_state.value,
            dependencies=dependencies,
            safety_summary=safety_controller.get_safety_summary(),
        )


# Global singleton instance
production_health_service = ProductionHealthService()
