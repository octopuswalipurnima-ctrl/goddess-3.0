"""
Tests for Stream-Specific Emergency Stop in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.manager import OperationsManager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_stream_specific_emergency_stop_isolates_affected_stream():
    """Verify emergency stop on STREAM_A does not halt STREAM_B."""
    mgr = OperationsManager()

    await mgr.trigger_emergency_stop(stream_id="STREAM_A", reason="Raid on Stream A")

    # Stream A must be halted
    can_a, _ = safety_controller.can_send_chat("STREAM_A")
    assert can_a is False

    # Stream B must remain operational
    can_b, _ = safety_controller.can_send_chat("STREAM_B")
    assert can_b is True
