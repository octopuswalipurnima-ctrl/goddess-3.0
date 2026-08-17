"""
Operations Telemetry Subsystem for GODDESS AI 2.0.

Provides real-time aggregated metrics across live streams, Gemini AI, YouTube providers,
and core infrastructure with bounded historical windows and percentile calculations.
"""

from collections import deque
from datetime import datetime, timezone
import math
import time
from typing import Deque, Dict, List, Optional

from app.core.logging import get_logger
from app.services.operations.models import (
    AIHealth,
    ComponentStatus,
    LatencyMetrics,
    ProviderOperations,
    SafeCredentialSummary,
    StreamOperations,
    SystemOverview,
)

logger = get_logger("operations.telemetry")

MAX_LATENCY_SAMPLES = 1000


class PercentileTracker:
    """Bounded sliding window for latency distribution calculation."""

    def __init__(self, max_samples: int = MAX_LATENCY_SAMPLES):
        self._samples: Deque[float] = deque(maxlen=max_samples)

    def record(self, latency_ms: float) -> None:
        if latency_ms >= 0.0:
            self._samples.append(latency_ms)

    def calculate(self) -> LatencyMetrics:
        if not self._samples:
            return LatencyMetrics()

        sorted_samples = sorted(self._samples)
        n = len(sorted_samples)

        def get_percentile(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_samples[int(k)]
            d0 = sorted_samples[int(f)] * (c - k)
            d1 = sorted_samples[int(c)] * (k - f)
            return round(d0 + d1, 2)

        p50 = get_percentile(0.50)
        p95 = get_percentile(0.95)
        p99 = get_percentile(0.99)
        avg = round(sum(sorted_samples) / n, 2)

        return LatencyMetrics(
            p50_ms=p50,
            p95_ms=p95,
            p99_ms=p99,
            average_ms=avg,
            sample_count=n,
        )


class OperationsTelemetryService:
    """Unified telemetry service collecting metrics without unbounded memory consumption."""

    def __init__(self):
        self._start_time = time.time()
        self._gemini_latency = PercentileTracker()
        self._youtube_latency = PercentileTracker()
        self._eventbus_latency = PercentileTracker()
        self._moderation_latency = PercentileTracker()
        self._cohost_latency = PercentileTracker()

        # Stream-specific telemetry counters (stream_id -> dict)
        self._stream_counters: Dict[str, Dict[str, int]] = {}

    def _get_stream_counts(self, stream_id: str) -> Dict[str, int]:
        if stream_id not in self._stream_counters:
            self._stream_counters[stream_id] = {
                "messages_received": 0,
                "messages_sent": 0,
                "moderation_actions": 0,
                "cohost_responses": 0,
                "reconnect_count": 0,
            }
        return self._stream_counters[stream_id]

    def record_message_received(self, stream_id: str) -> None:
        self._get_stream_counts(stream_id)["messages_received"] += 1

    def record_message_sent(self, stream_id: str) -> None:
        self._get_stream_counts(stream_id)["messages_sent"] += 1

    def record_moderation_action(self, stream_id: str, latency_ms: float = 0.0) -> None:
        self._get_stream_counts(stream_id)["moderation_actions"] += 1
        if latency_ms > 0:
            self._moderation_latency.record(latency_ms)

    def record_cohost_response(self, stream_id: str, latency_ms: float = 0.0) -> None:
        self._get_stream_counts(stream_id)["cohost_responses"] += 1
        if latency_ms > 0:
            self._cohost_latency.record(latency_ms)

    def record_gemini_request(self, latency_ms: float) -> None:
        self._gemini_latency.record(latency_ms)

    def record_youtube_request(self, latency_ms: float) -> None:
        self._youtube_latency.record(latency_ms)

    def get_system_overview(self) -> SystemOverview:
        uptime = round(time.time() - self._start_time, 1)
        tot_msgs = sum(c["messages_received"] for c in self._stream_counters.values())
        tot_mod = sum(c["moderation_actions"] for c in self._stream_counters.values())
        tot_cohost = sum(c["cohost_responses"] for c in self._stream_counters.values())

        from app.core.safety_controller import safety_controller
        return SystemOverview(
            system_status=ComponentStatus.HEALTHY if not safety_controller.is_global_emergency else ComponentStatus.DEGRADED,
            production_mode="PRODUCTION_SAFE",
            safety_state=safety_controller.global_state,
            uptime_seconds=uptime,
            active_streams_count=len(self._stream_counters),
            total_messages_processed=tot_msgs,
            total_moderation_actions=tot_mod,
            total_cohost_responses=tot_cohost,
        )

    def get_ai_health(self) -> AIHealth:
        from app.services.gemini.credentials import gemini_credentials
        from app.services.gemini.models import CredentialState
        from app.services.gemini.manager import gemini_manager

        creds = gemini_credentials.get_health_summary()
        total_keys = sum(1 for c in creds if c.state != CredentialState.UNCONFIGURED)
        healthy_keys = sum(1 for c in creds if c.state == CredentialState.AVAILABLE)

        if total_keys == 0:
            status = ComponentStatus.NOT_CONFIGURED
        elif healthy_keys == 0:
            status = ComponentStatus.UNAVAILABLE
        elif healthy_keys < total_keys:
            status = ComponentStatus.DEGRADED

        metrics = gemini_manager.metrics

        return AIHealth(
            provider_status=status,
            healthy_credentials=healthy_keys,
            total_credentials=total_keys,
            request_count=metrics.total_requests,
            success_count=metrics.successful_requests,
            failure_count=metrics.failed_requests,
            quota_failures=metrics.rate_limited_count,
            fallback_count=metrics.model_fallbacks_count,
            queue_depth=metrics.queued_requests,
            latency=self._gemini_latency.calculate(),
        )

    def get_provider_operations(self) -> Dict[str, ProviderOperations]:
        from app.services.youtube.credentials import youtube_credentials
        from app.services.gemini.credentials import gemini_credentials
        from app.services.gemini.models import CredentialState

        # YouTube Summary
        yt_creds = youtube_credentials.get_health_summary()
        yt_safe_creds = [
            SafeCredentialSummary(
                key_alias=f"KEY-{i+1}",
                state=c.state.value if hasattr(c.state, "value") else str(c.state),
                total_requests=c.total_requests,
                failed_requests=c.failed_requests,
                consecutive_failures=c.consecutive_failures,
                cooldown_until=c.cooldown_until,
            )
            for i, c in enumerate(yt_creds)
        ]
        yt_healthy = sum(1 for c in yt_creds if c.state == CredentialState.AVAILABLE)
        yt_cooldown = sum(1 for c in yt_creds if c.state == CredentialState.COOLDOWN)
        yt_failed = sum(1 for c in yt_creds if c.state == CredentialState.FAILED)
        yt_status = ComponentStatus.HEALTHY if yt_healthy > 0 else (ComponentStatus.NOT_CONFIGURED if len(yt_creds) == 0 else ComponentStatus.UNAVAILABLE)

        yt_ops = ProviderOperations(
            provider_name="YouTube Data API v3",
            status=yt_status,
            total_keys=len(yt_creds),
            healthy_keys=yt_healthy,
            cooldown_keys=yt_cooldown,
            failed_keys=yt_failed,
            credentials=yt_safe_creds,
            quota_failures=sum(c.quota_failures for c in yt_creds),
            total_requests=sum(c.total_requests for c in yt_creds),
            request_failures=sum(c.failed_requests for c in yt_creds),
        )

        # Gemini Summary
        g_creds = gemini_credentials.get_health_summary()
        g_safe_creds = [
            SafeCredentialSummary(
                key_alias=f"KEY-{i+1}",
                state=c.state.value if hasattr(c.state, "value") else str(c.state),
                total_requests=c.total_requests,
                failed_requests=c.failed_requests,
                consecutive_failures=c.consecutive_failures,
                cooldown_until=c.cooldown_until,
            )
            for i, c in enumerate(g_creds)
        ]
        g_healthy = sum(1 for c in g_creds if c.state == CredentialState.AVAILABLE)
        g_cooldown = sum(1 for c in g_creds if c.state == CredentialState.COOLDOWN)
        g_failed = sum(1 for c in g_creds if c.state == CredentialState.FAILED)
        g_status = ComponentStatus.HEALTHY if g_healthy > 0 else (ComponentStatus.NOT_CONFIGURED if len(g_creds) == 0 else ComponentStatus.UNAVAILABLE)

        g_ops = ProviderOperations(
            provider_name="Google Gemini API",
            status=g_status,
            total_keys=len(g_creds),
            healthy_keys=g_healthy,
            cooldown_keys=g_cooldown,
            failed_keys=g_failed,
            credentials=g_safe_creds,
            quota_failures=sum(c.quota_failures for c in g_creds),
            total_requests=sum(c.total_requests for c in g_creds),
            request_failures=sum(c.failed_requests for c in g_creds),
        )

        return {"youtube": yt_ops, "gemini": g_ops}


# Global singleton instance
operations_telemetry_service = OperationsTelemetryService()
