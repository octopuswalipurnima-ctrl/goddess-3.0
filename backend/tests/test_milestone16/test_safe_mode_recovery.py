"""
Tests for Safe Mode Transitions and Recovery in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_safe_mode_transition_and_clearance():
    """Verify stream transitions to SAFE_MODE and recovers to NORMAL."""
    await safety_controller.enable_safe_mode("STREAM_A", reason="High Chat Surge")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.SAFE_MODE

    await safety_controller.disable_safe_mode("STREAM_A")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.NORMAL
