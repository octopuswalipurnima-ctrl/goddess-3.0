"""
Tests for Provider Failure Matrix in GODDESS AI 2.0.
"""

import pytest
from app.core.circuit_breaker import circuit_breakers


def test_circuit_breaker_registry_isolation():
    """Verify tripping one circuit breaker does not trip another."""
    cb_yt = circuit_breakers.get("youtube")
    cb_g = circuit_breakers.get("gemini")

    cb_yt.reset()
    cb_g.reset()

    # Trip YouTube breaker
    for _ in range(10):
        cb_yt.record_failure()

    assert cb_yt.state.value == "OPEN"
    assert cb_g.state.value == "CLOSED"
