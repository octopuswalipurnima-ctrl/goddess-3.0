"""
Tests for Duplicate Message Protection & Idempotency in GODDESS AI 2.0.
"""

import asyncio
import pytest
from app.core.events import event_bus
from app.services.youtube.chat import LiveChatReader
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_duplicate_messages_cross_reconnect_dedup():
    """Verify identical message IDs across polling cycles are ingested exactly once."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_DEDUP_1", live_chat_id="chat_dedup_1")

    # Queue message with static ID
    fake_api.queue_chat_message("chat_dedup_1", "UserA", "Unique msg", message_id="static_msg_id_100")

    dispatched = []

    async def msg_handler(data):
        if data.get("stream_id") == "STREAM_DEDUP_1":
            dispatched.append(data)

    event_bus.subscribe("CHAT_MESSAGE", msg_handler)

    reader = LiveChatReader(stream_id="STREAM_DEDUP_1", live_chat_id="chat_dedup_1", api_client=fake_api)
    await reader.start()

    await asyncio.sleep(0.15)
    assert len(dispatched) == 1

    # Queue exact same message again (simulating YouTube delivering duplicate across reconnect)
    fake_api.queue_chat_message("chat_dedup_1", "UserA", "Unique msg", message_id="static_msg_id_100")
    await asyncio.sleep(0.15)
    await reader.stop()

    # Must still be exactly 1
    assert len(dispatched) == 1
    assert reader.metrics.messages_received == 1
