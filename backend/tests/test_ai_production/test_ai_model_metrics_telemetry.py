"""
Tests for AI Observability & Performance Metrics Telemetry in GODDESS AI 2.0.
"""

from app.services.gemini.models import GeminiMetrics


def test_gemini_metrics_telemetry_accounting():
    """Verify GeminiMetrics accurately tracks requests, errors, and latencies safely."""
    metrics = GeminiMetrics()
    metrics.total_requests = 100
    metrics.successful_requests = 95
    metrics.failed_requests = 5
    metrics.model_fallbacks_count = 3
    metrics.rate_limited_count = 1
    metrics.total_latency_seconds = 12.5

    summary = metrics.model_dump()
    assert summary["total_requests"] == 100
    assert summary["successful_requests"] == 95
    assert summary["failed_requests"] == 5
    assert summary["model_fallbacks_count"] == 3
    assert metrics.average_latency_seconds > 0
    assert "api_key" not in summary
    assert "token" not in summary
