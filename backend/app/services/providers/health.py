"""
Unified Provider Health & Telemetry Service for GODDESS AI 2.0.

Aggregates operational metrics, failure rates, and safe credential status
across YouTube Data API and Google Gemini AI providers with zero raw secret exposure.
"""

from datetime import datetime, timezone
import statistics
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.gemini.credentials import gemini_credentials
from app.services.gemini.manager import gemini_manager
from app.services.youtube.credentials import youtube_credentials
from app.services.youtube.stream_manager import stream_manager


class ProviderHealth(BaseModel):
    """Safe telemetry model for an external service provider."""
    provider: str = Field(description="'youtube' or 'gemini'")
    status: str = Field(description="'HEALTHY', 'DEGRADED', 'UNAVAILABLE', or 'NOT_CONFIGURED'")
    credential_count: int = 0
    healthy_count: int = 0
    cooldown_count: int = 0
    unavailable_count: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    quota_failures: int = 0
    failure_rate: float = 0.0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    latency_metrics: Dict[str, Any] = Field(default_factory=dict)
    credentials: List[Dict[str, Any]] = Field(default_factory=list)


class ProviderHealthService:
    """Service providing safe, structured provider telemetry."""

    @staticmethod
    def get_youtube_provider_health() -> ProviderHealth:
        """Aggregate safe health and usage metrics for YouTube provider."""
        slots = youtube_credentials.get_health_summary()
        configured = youtube_credentials.configured_count
        available = youtube_credentials.available_count
        cooldown = sum(1 for s in slots if s.state.value == "COOLDOWN")
        unavailable = sum(1 for s in slots if s.state.value in ("FAILED", "DISABLED"))

        total_reqs = sum(s.total_requests for s in slots)
        success_reqs = sum(s.successful_requests for s in slots)
        failed_reqs = sum(s.failed_requests for s in slots)
        quota_fails = sum(s.quota_failures for s in slots)

        failure_rate = (
            round(failed_reqs / total_reqs, 4) if total_reqs > 0 else 0.0
        )

        last_success = None
        last_failure = None
        for s in slots:
            if s.last_used_at and (not last_success or s.last_used_at > last_success):
                last_success = s.last_used_at
            if s.last_error and (not last_failure or (s.last_used_at and s.last_used_at > last_failure)):
                last_failure = s.last_used_at

        # Determine status
        if configured == 0:
            status = "NOT_CONFIGURED"
        elif available == 0:
            status = "UNAVAILABLE"
        elif available < configured or failure_rate > 0.2:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        return ProviderHealth(
            provider="youtube",
            status=status,
            credential_count=configured,
            healthy_count=available,
            cooldown_count=cooldown,
            unavailable_count=unavailable,
            total_requests=total_reqs,
            successful_requests=success_reqs,
            failed_requests=failed_reqs,
            quota_failures=quota_fails,
            failure_rate=failure_rate,
            last_success=last_success,
            last_failure=last_failure,
            latency_metrics={
                "active_streams": stream_manager.active_stream_count,
                "max_concurrent_streams": stream_manager.max_concurrent_streams,
            },
            credentials=[s.model_dump() for s in slots],
        )

    @staticmethod
    def get_gemini_provider_health() -> ProviderHealth:
        """Aggregate safe health and usage metrics for Gemini provider."""
        slots = gemini_credentials.get_health_summary()
        configured = gemini_credentials.configured_count
        available = gemini_credentials.available_count
        cooldown = sum(1 for s in slots if s.state.value == "COOLDOWN")
        unavailable = sum(1 for s in slots if s.state.value in ("FAILED", "DISABLED"))

        total_reqs = gemini_manager.metrics.total_requests or sum(s.total_requests for s in slots)
        success_reqs = gemini_manager.metrics.successful_requests or sum(s.successful_requests for s in slots)
        failed_reqs = gemini_manager.metrics.failed_requests or sum(s.failed_requests for s in slots)
        quota_fails = sum(s.quota_failures for s in slots)

        failure_rate = (
            round(failed_reqs / total_reqs, 4) if total_reqs > 0 else 0.0
        )

        last_success = None
        last_failure = None
        for s in slots:
            if s.last_used_at and (not last_success or s.last_used_at > last_success):
                last_success = s.last_used_at
            if s.last_error and (not last_failure or (s.last_used_at and s.last_used_at > last_failure)):
                last_failure = s.last_used_at

        # Determine status
        if configured == 0:
            status = "NOT_CONFIGURED"
        elif available == 0:
            status = "UNAVAILABLE"
        elif available < configured or failure_rate > 0.2:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        return ProviderHealth(
            provider="gemini",
            status=status,
            credential_count=configured,
            healthy_count=available,
            cooldown_count=cooldown,
            unavailable_count=unavailable,
            total_requests=total_reqs,
            successful_requests=success_reqs,
            failed_requests=failed_reqs,
            quota_failures=quota_fails,
            failure_rate=failure_rate,
            last_success=last_success,
            last_failure=last_failure,
            latency_metrics={
                "active_requests": gemini_manager.queue.active_count,
                "queued_requests": gemini_manager.queue.queued_count,
                "primary_model": gemini_manager.router.primary_model if hasattr(gemini_manager, "router") else "gemini-2.5-flash",
                "fallback_model": gemini_manager.router.fallback_model if hasattr(gemini_manager, "router") else "gemini-2.5-flash-lite",
            },
            credentials=[s.model_dump() for s in slots],
        )

    @classmethod
    def get_all_providers_health(cls) -> Dict[str, ProviderHealth]:
        """Return combined provider telemetry map."""
        return {
            "youtube": cls.get_youtube_provider_health(),
            "gemini": cls.get_gemini_provider_health(),
        }


# Singleton instance
provider_health_service = ProviderHealthService()
