"""
Tests for Command Safety Hardening and Idempotency in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
import pytest
from app.core.idempotency import idempotency_manager
from app.modules.commands.module import CommandsModule
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_command_safety_and_idempotency_block():
    """Verify commands execute safely and duplicate message IDs do not double-execute."""
    idempotency_manager.clear()
    cmd_mod = CommandsModule()

    msg_data = {
        "message_id": "msg_cmd_999",
        "stream_id": "STREAM_A",
        "author_name": "Viewer1",
        "author_id": "usr_101",
        "message_text": "!help",
        "published_at": datetime.now(timezone.utc),
    }

    # First run
    await cmd_mod.handle_event("CHAT_MESSAGE", msg_data)
    initial_count = cmd_mod.metrics["commands_executed"]

    # Duplicate message with same ID
    await cmd_mod.handle_event("CHAT_MESSAGE", msg_data)
    assert cmd_mod.metrics["commands_executed"] == initial_count
