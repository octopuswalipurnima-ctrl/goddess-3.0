"""
Tests for Command Stream Isolation & Safety Gating in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller
from app.modules.commands.module import CommandsModule
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_command_blocked_when_emergency_stop_active():
    """Verify command execution is skipped when emergency stop is active on that stream."""
    cmd_mod = CommandsModule()
    cmd_mod.state = "RUNNING"

    await safety_controller.trigger_emergency_stop(stream_id="STREAM_CMD_STOP", reason="Lockdown")

    msg = ChatMessage(
        message_id="msg_cmd_stop",
        stream_id="STREAM_CMD_STOP",
        author_id="user_1",
        author_name="User",
        message_text="!help",
    )

    await cmd_mod.handle_event("CHAT_MESSAGE", msg.model_dump())
    # Command should not have executed
    assert cmd_mod.metrics["commands_executed"] == 0

    await safety_controller.clear_emergency_stop(stream_id="STREAM_CMD_STOP")
