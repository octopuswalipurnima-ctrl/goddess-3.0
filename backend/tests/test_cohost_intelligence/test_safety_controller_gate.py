"""
Tests for SafetyController Gating over Co-Host in GODDESS AI 2.0.
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
async def test_safety_controller_can_cohost_gate_blocks_generation():
    """Verify SafetyController blocking prevents any AI generation or outgoing messages."""
    mgr = CoHostManager()
    mgr.update_config("STREAM_SAFE", {"enabled": True, "dry_run": False})

    # Trigger emergency stop on STREAM_SAFE
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_SAFE", reason="Raid in progress")

    msg = ChatMessage(
        message_id="msg_gate_1",
        stream_id="STREAM_SAFE",
        author_id="user_1",
        author_name="Alice",
        message_text="Hello Goddess?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)
    assert resp is None
