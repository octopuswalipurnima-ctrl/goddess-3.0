"""
Tests for Safe Mode Co-Host Behavior and Zero Replay in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.cohost.manager import CoHostManager
from app.services.youtube.models import ChatMessage


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_safe_mode_suppresses_cohost_and_disabling_does_not_replay():
    """Verify Safe Mode suppresses Co-Host generation, and disabling it does not replay past messages."""
    mgr = CoHostManager()
    mgr.update_config("STREAM_SAFE_NO_REPLAY", {"enabled": True, "dry_run": False})

    # Enable Safe Mode
    await safety_controller.enable_safe_mode(stream_id="STREAM_SAFE_NO_REPLAY", reason="High chatter surge")

    msg = ChatMessage(
        message_id="msg_sm_1",
        stream_id="STREAM_SAFE_NO_REPLAY",
        author_id="user_1",
        author_name="Alice",
        message_text="Hey Goddess?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)
    assert resp is None  # Blocked during safe mode

    # Disable Safe Mode
    await safety_controller.disable_safe_mode(stream_id="STREAM_SAFE_NO_REPLAY")

    # Verify past message is not re-evaluated or re-sent
    assert mgr.metrics.responses_sent == 0
