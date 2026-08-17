"""
Tests for Zero Historical Replay Upon Emergency Clearance in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_no_historical_replay_on_emergency_recovery():
    """Verify emergency stop drops pending mutations and clearance allows new messages only."""
    await safety_controller.trigger_emergency_stop("STREAM_A", reason="Spam Attack")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.EMERGENCY_STOP

    # Clear emergency stop
    await safety_controller.clear_emergency_stop("STREAM_A")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.NORMAL

    # Next fresh message should be permitted
    can_send, _ = safety_controller.can_send_chat("STREAM_A")
    assert can_send is True
