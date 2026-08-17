"""
Emergency Stop End-to-End Tests for GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    """Ensure clean safety controller state before and after each test."""
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_global_emergency_stop_halts_all_streams_idempotently():
    """Verify global emergency stop blocks moderation, cohost, commands across all streams."""
    streams = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]

    # Trigger global stop
    await safety_controller.trigger_emergency_stop(stream_id=None, reason="Critical drill")

    assert safety_controller.global_state == SafetyState.EMERGENCY_STOP
    assert safety_controller.is_global_emergency is True

    # Check all streams blocked
    for s in streams:
        can_mod, _ = safety_controller.can_moderate(s)
        can_co, _ = safety_controller.can_cohost(s)
        can_chat, _ = safety_controller.can_send_chat(s)
        assert can_mod is False
        assert can_co is False
        assert can_chat is False

    # Second stop call must be idempotent
    await safety_controller.trigger_emergency_stop(stream_id=None, reason="Duplicate trigger")
    assert safety_controller.global_state == SafetyState.EMERGENCY_STOP

    # Clear global emergency stop
    await safety_controller.clear_emergency_stop(stream_id=None)
    assert safety_controller.global_state == SafetyState.NORMAL
    assert safety_controller.is_global_emergency is False


@pytest.mark.asyncio
async def test_stream_specific_emergency_stop_isolates_unaffected_streams():
    """Verify emergency stop on STREAM_A halts STREAM_A while STREAM_B continues operating normally."""
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_A", reason="Raid on Stream A")

    # Stream A is blocked
    can_mod_a, _ = safety_controller.can_moderate("STREAM_A")
    assert can_mod_a is False

    # Stream B remains operational
    can_mod_b, _ = safety_controller.can_moderate("STREAM_B")
    can_co_b, _ = safety_controller.can_cohost("STREAM_B")
    assert can_mod_b is True
    assert can_co_b is True

    # Clear Stream A
    await safety_controller.clear_emergency_stop(stream_id="STREAM_A")
    can_mod_a_cleared, _ = safety_controller.can_moderate("STREAM_A")
    assert can_mod_a_cleared is True
