"""
Tests for YouTube Reconnect Engine & Exponential Backoff in GODDESS AI 2.0.
"""

import asyncio
import pytest
from app.services.youtube.chat import LiveChatReader
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_reconnect_engine_transient_error_backoff():
    """Verify transient error triggers reconnect attempt, increments counter, and recovers."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_RECONNECT_1", live_chat_id="chat_reconnect_1")

    # Configure 1 transient network failure
    fake_api.network_error_count = 1
    fake_api.queue_chat_message("chat_reconnect_1", "Viewer1", "Recovered message")

    reader = LiveChatReader(stream_id="STREAM_RECONNECT_1", live_chat_id="chat_reconnect_1", api_client=fake_api)
    await reader.start()

    # Wait for failure and retry cycle
    await asyncio.sleep(1.2)
    await reader.stop()

    assert reader.metrics.reconnect_count >= 1
    assert reader.metrics.polling_errors >= 1
    assert reader.metrics.messages_received >= 1
