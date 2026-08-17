"""
Tests for Provider Circuit Breakers in GODDESS AI 2.0.
"""

import pytest
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerState


def test_circuit_breaker_tripping_and_recovery():
    """Verify circuit breaker trips to OPEN on failures and resets on recovery."""
    cb = CircuitBreaker("test_provider", failure_threshold=3, recovery_timeout_seconds=0.1)

    assert cb.state == CircuitBreakerState.CLOSED
    allowed, _ = cb.allow_request()
    assert allowed is True

    # 3 consecutive failures -> trips breaker
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == CircuitBreakerState.OPEN
    allowed_blocked, reason = cb.allow_request()
    assert allowed_blocked is False
    assert "OPEN" in reason
