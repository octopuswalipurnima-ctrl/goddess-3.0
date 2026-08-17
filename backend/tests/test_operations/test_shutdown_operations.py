"""
Tests for Graceful Shutdown Operations in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_shutdown_transitions_safety_controller():
    """Verify shutting down state blocks all further incoming actions."""
    await safety_controller.enter_shutting_down()
    assert safety_controller.is_shutting_down is True
    assert safety_controller.global_state == SafetyState.SHUTTING_DOWN

    can_chat, _ = safety_controller.can_send_chat("STREAM_A")
    assert can_chat is False
