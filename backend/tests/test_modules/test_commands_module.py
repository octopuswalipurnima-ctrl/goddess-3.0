"""
Tests for CommandsModule: normalization, cooldowns, stream isolation, and safety.
"""

import pytest

from app.modules.commands.module import CommandsModule
from app.modules.models import StreamModuleConfig


@pytest.mark.asyncio
async def test_commands_module_parsing_and_stream_isolation():
    mod = CommandsModule()

    # Disabled on stream_1 by default -> ignored
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m1",
            "author_id": "u1",
            "author_name": "Alice",
            "message_text": "!help",
        },
    )
    assert mod.metrics["commands_executed"] == 0

    # Enable on stream_1
    mod.update_stream_config("stream_1", StreamModuleConfig(enabled=True))

    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m2",
            "author_id": "u1",
            "author_name": "Alice",
            "message_text": "  !HELP  ",
        },
    )
    assert mod.metrics["commands_executed"] == 1

    # Immediate duplicate from same user triggers cooldown block
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m3",
            "author_id": "u1",
            "author_name": "Alice",
            "message_text": "!help",
        },
    )
    assert mod.metrics["commands_executed"] == 1
    assert mod.metrics["commands_blocked_cooldown"] == 1
