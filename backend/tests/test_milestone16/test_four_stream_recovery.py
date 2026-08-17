"""
Tests for 4-Stream Independent Recovery in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_stream_independent_clearance_recovery():
    """Verify clearing one stream leaves others in their current individual state."""
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_A", reason="Issue A")
    await safety_controller.enable_safe_mode("STREAM_B", reason="Issue B")

    # Clear A
    await safety_controller.clear_emergency_stop(stream_id="STREAM_A")

    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.NORMAL
    assert safety_controller.get_stream_state("STREAM_B") == SafetyState.SAFE_MODE
