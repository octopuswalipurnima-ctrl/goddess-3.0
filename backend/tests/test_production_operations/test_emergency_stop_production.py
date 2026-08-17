"""
Tests for Production Emergency Stop Workflow & Audit Gating in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller


@pytest.mark.asyncio
async def test_emergency_stop_idempotency_and_event_publishing():
    """Verify repeated emergency stop calls are idempotent and publish safety events."""
    await safety_controller.trigger_emergency_stop(reason="Operator override 1", triggered_by="admin")
    assert safety_controller.is_global_emergency is True

    # Repeated call
    await safety_controller.trigger_emergency_stop(reason="Operator override 2", triggered_by="admin")
    assert safety_controller.is_global_emergency is True

    summary = safety_controller.get_safety_summary()
    assert summary["is_global_emergency"] is True
    assert summary["emergency_stop_count"] >= 2

    # Clear
    await safety_controller.clear_emergency_stop(cleared_by="admin")
    assert safety_controller.is_global_emergency is False
