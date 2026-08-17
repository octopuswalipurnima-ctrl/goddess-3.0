"""
Tests for YouTube Live Chat Reader Ingestion & Events in GODDESS AI 2.0.
"""

import asyncio
import pytest
from app.core.events import event_bus
from app.services.youtube.chat import LiveChatReader
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_live_chat_reader_message_ingestion():
    """Verify LiveChatReader ingests queued messages and dispatches CHAT_MESSAGE events."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_READER_1", live_chat_id="chat_reader_1")

    # Queue 2 test messages
    fake_api.queue_chat_message("chat_reader_1", author_name="Viewer1", message_text="Hello Goddess!")
    fake_api.queue_chat_message("chat_reader_1", author_name="Viewer2", message_text="Can you hear me?")

    received_events = []

    async def chat_handler(data):
        received_events.append(data)

    event_bus.subscribe("CHAT_MESSAGE", chat_handler)

    reader = LiveChatReader(stream_id="STREAM_READER_1", live_chat_id="chat_reader_1", api_client=fake_api)
    await reader.start()

    # Allow polling loop to process
    await asyncio.sleep(0.15)
    await reader.stop()

    assert reader.metrics.messages_received == 2
    assert len(received_events) >= 2
    texts = [e["message"]["message_text"] for e in received_events if e["stream_id"] == "STREAM_READER_1"]
    assert "Hello Goddess!" in texts
    assert "Can you hear me?" in texts
