"""
Tests for YouTube Live Chat Writer & Validation in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.exceptions import ChatMessageValidationError, LiveChatUnavailableError
from app.services.youtube.stream_session import StreamSession
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_chat_writer_length_and_empty_validation():
    """Verify validation gates on outgoing chat messages (1-200 chars)."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_WRITER_1", live_chat_id="chat_writer_1")

    session = StreamSession(stream_id="STREAM_WRITER_1", api_client=fake_api)
    await session.start()

    # Empty message
    with pytest.raises(ChatMessageValidationError):
        await session.send_chat_message("")

    # Whitespace only
    with pytest.raises(ChatMessageValidationError):
        await session.send_chat_message("   ")

    # Exceeding 200 characters
    long_msg = "A" * 201
    with pytest.raises(ChatMessageValidationError):
        await session.send_chat_message(long_msg)

    # Valid message
    sent = await session.send_chat_message("Hello world from GODDESS AI!")
    assert sent.message_text == "Hello world from GODDESS AI!"
    assert session.metrics.messages_sent == 1
    assert len(fake_api.sent_messages) == 1

    await session.stop()


@pytest.mark.asyncio
async def test_chat_writer_raises_when_no_live_chat():
    """Verify LiveChatUnavailableError is raised if stream has no active liveChatId."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_NO_CHAT", live_chat_id=None)

    session = StreamSession(stream_id="STREAM_NO_CHAT", api_client=fake_api)
    # Stream with no live_chat_id
    session.stream_info = fake_api.streams["STREAM_NO_CHAT"]
    session.stream_info.live_chat_id = None

    with pytest.raises(LiveChatUnavailableError):
        await session.send_chat_message("This should fail.")
