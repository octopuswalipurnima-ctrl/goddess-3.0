"""
Tests for AI Operations and Latency Percentiles in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.manager import OperationsManager


def test_ai_operations_latency_calculation():
    """Verify latency percentile metrics calculations."""
    mgr = OperationsManager()

    # Record simulated latency points
    for latency in [100.0, 120.0, 130.0, 150.0, 200.0]:
        mgr.telemetry.record_gemini_request(latency)

    ai_health = mgr.get_ai_health()
    assert ai_health.latency.sample_count >= 5
    assert ai_health.latency.p50_ms > 0.0
    assert ai_health.latency.p95_ms >= ai_health.latency.p50_ms
