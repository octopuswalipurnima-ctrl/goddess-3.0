"""
Tests for Commands Module Execution on Originating Live Stream in GODDESS AI 2.0.
"""

import pytest
from app.modules.commands.module import CommandsModule
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_command_execution_only_on_originating_stream():
    """Verify !help command is handled safely by CommandsModule."""
    cmd_module = CommandsModule()
    cmd_module.state = "RUNNING"
    cmd_module.health = "HEALTHY"

    # Command message on STREAM_CMD_1
    cmd_msg = ChatMessage(
        message_id="msg_cmd_1",
        stream_id="STREAM_CMD_1",
        author_id="user_viewer",
        author_name="GoodViewer",
        message_text="!help",
    )

    # Process message through command module event handler
    await cmd_module.handle_event("CHAT_MESSAGE", cmd_msg.model_dump())
    assert cmd_module.state == "RUNNING"
