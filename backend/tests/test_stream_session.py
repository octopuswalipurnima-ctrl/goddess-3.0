"""
Tests for StreamSession Lifecycle and Isolation.
"""

import pytest
from app.services.youtube.models import ChatMessage, LiveStreamInfo, StreamStatus
from app.services.youtube.stream_session import StreamSession


class MockSessionAPIClient:
    """Mock client for testing StreamSession lifecycle."""

    def __init__(self, stream_info: LiveStreamInfo):
        self.stream_info = stream_info

    async def get_live_stream_details(self, stream_id: str):
        return self.stream_info

    async def send_chat_message(self, live_chat_id: str, message_text: str):
        return ChatMessage(
            message_id="sent_101",
            stream_id=live_chat_id,
            channel_id="ch_owner",
            author_id="bot_id",
            author_name="GoddessBot",
            message_text=message_text,
            published_at="2026-08-16T12:00:00Z",
        )

    async def get_live_chat_messages(self, live_chat_id: str, page_token: str = None):
        return [], None, 1000


@pytest.mark.asyncio
async def test_stream_session_lifecycle():
    """Verify StreamSession state transitions."""
    info = LiveStreamInfo(
        stream_id="stream_001",
        channel_id="channel_xyz",
        title="Gaming Championship Live",
        status=StreamStatus.LIVE,
        concurrent_viewers=350,
        live_chat_id="chat_001",
    )
    mock_client = MockSessionAPIClient(info)
    session = StreamSession("stream_001", api_client=mock_client)

    assert session.status == StreamStatus.STANDBY
    assert session.is_active is False

    # Start session
    await session.start()
    assert session.status == StreamStatus.LIVE
    assert session.is_active is True
    assert session.stream_info.concurrent_viewers == 350

    # Send outgoing chat message
    sent = await session.send_chat_message("Hello from Goddess AI!")
    assert sent.message_id == "sent_101"
    assert session.metrics.messages_published == 1

    # Export summary
    summary = session.to_summary()
    assert summary.stream_id == "stream_001"
    assert summary.title == "Gaming Championship Live"
    assert summary.status == StreamStatus.LIVE

    # Stop session
    await session.stop(reason="Test ended")
    assert session.status == StreamStatus.ENDED
    assert session.is_active is False
