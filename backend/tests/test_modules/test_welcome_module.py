"""
Tests for WelcomeModule: new chatter detection, cooldowns, and disabled defaults.
"""

import pytest

from app.modules.models import StreamModuleConfig
from app.modules.welcome.module import WelcomeModule


@pytest.mark.asyncio
async def test_welcome_module_lifecycle_and_cooldown():
    mod = WelcomeModule()

    # Disabled by default
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m1",
            "author_id": "u1",
            "author_name": "Bob",
            "message_text": "Hey everyone!",
        },
    )
    assert mod.metrics["welcomes_sent"] == 0

    # Enable on stream_1
    mod.update_stream_config("stream_1", StreamModuleConfig(enabled=True))

    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m2",
            "author_id": "u1",
            "author_name": "Bob",
            "message_text": "First time here!",
        },
    )
    assert mod.metrics["welcomes_sent"] == 1

    # Second message from Bob within cooldown -> no double welcome
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m3",
            "author_id": "u1",
            "author_name": "Bob",
            "message_text": "Loving the vibes!",
        },
    )
    assert mod.metrics["welcomes_sent"] == 1
