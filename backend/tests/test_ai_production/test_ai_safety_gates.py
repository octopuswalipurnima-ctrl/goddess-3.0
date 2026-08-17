"""
Tests for Safety Controller Gates on AI Operations in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller


@pytest.mark.asyncio
async def test_safety_controller_blocks_cohost_in_safe_mode():
    """Verify can_cohost returns False when safe mode is active on a stream."""
    await safety_controller.enable_safe_mode(stream_id="STREAM_SAFE_AI", reason="Chat volatility")

    can_cohost, reason = safety_controller.can_cohost("STREAM_SAFE_AI")
    assert can_cohost is False
    assert "Safe mode" in reason

    await safety_controller.disable_safe_mode(stream_id="STREAM_SAFE_AI")
    can_cohost, _ = safety_controller.can_cohost("STREAM_SAFE_AI")
    assert can_cohost is True


@pytest.mark.asyncio
async def test_safety_controller_blocks_outgoing_chat_during_emergency():
    """Verify can_send_chat returns False during emergency stop."""
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_EMERGENCY_AI", reason="Security lock")

    can_chat, reason = safety_controller.can_send_chat("STREAM_EMERGENCY_AI")
    assert can_chat is False
    assert "Emergency Stop" in reason

    await safety_controller.clear_emergency_stop(stream_id="STREAM_EMERGENCY_AI")
