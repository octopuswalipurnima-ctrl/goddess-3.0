"""
Tests for 4-Stream Failure Isolation in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_single_stream_emergency_does_not_affect_peers():
    """Verify emergency stop on STREAM_A does not alter STREAM_B, STREAM_C, or STREAM_D."""
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_A", reason="Stream A Overload")

    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.EMERGENCY_STOP
    assert safety_controller.get_stream_state("STREAM_B") == SafetyState.NORMAL
    assert safety_controller.get_stream_state("STREAM_C") == SafetyState.NORMAL
    assert safety_controller.get_stream_state("STREAM_D") == SafetyState.NORMAL
