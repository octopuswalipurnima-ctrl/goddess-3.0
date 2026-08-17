"""
Safe Mode Suppression and Zero-Replay Tests for GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    """Ensure clean safety controller state before and after each test."""
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_safe_mode_blocks_outgoing_chat_and_cohost():
    """Verify Safe Mode allows read evaluation but blocks live outgoing actions."""
    await safety_controller.enable_safe_mode(stream_id="STREAM_SAFE_1", reason="Chat surge")

    can_co, reason = safety_controller.can_cohost("STREAM_SAFE_1")
    can_chat, chat_reason = safety_controller.can_send_chat("STREAM_SAFE_1")

    assert can_co is False
    assert can_chat is False
    assert "Safe mode" in reason

    # Clear safe mode
    await safety_controller.disable_safe_mode(stream_id="STREAM_SAFE_1")
    can_co_restored, _ = safety_controller.can_cohost("STREAM_SAFE_1")
    can_chat_restored, _ = safety_controller.can_send_chat("STREAM_SAFE_1")

    assert can_co_restored is True
    assert can_chat_restored is True
