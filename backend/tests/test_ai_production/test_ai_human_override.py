"""
Tests for Human Operator Overrides over AI Decisions in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller


@pytest.mark.asyncio
async def test_human_operator_can_override_and_halt_stream():
    """Verify human operator can override AI automation by invoking emergency stop."""
    can_mod, _ = safety_controller.can_moderate("STREAM_OVERRIDE")
    assert can_mod is True

    # Operator invokes stop
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_OVERRIDE", reason="Human intervention", triggered_by="streamer")

    can_mod, reason = safety_controller.can_moderate("STREAM_OVERRIDE")
    assert can_mod is False
    assert "Human intervention" in reason

    await safety_controller.clear_emergency_stop(stream_id="STREAM_OVERRIDE", cleared_by="streamer")
