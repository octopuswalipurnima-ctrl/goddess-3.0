"""
Tests for YouTube Live Stream Session Lifecycle in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.models import StreamStatus
from app.services.youtube.stream_session import StreamSession
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_stream_session_lifecycle_live_and_stop():
    """Verify StreamSession transitions from STANDBY -> CONNECTING -> LIVE -> ENDED."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_TEST_1", title="Live Gaming Session", live_chat_id="chat_test_1")

    session = StreamSession(stream_id="STREAM_TEST_1", api_client=fake_api)
    assert session.status == StreamStatus.STANDBY
    assert session.is_active is False

    await session.start()
    assert session.status == StreamStatus.LIVE
    assert session.is_active is True
    assert session.stream_info.title == "Live Gaming Session"
    assert session.stream_info.live_chat_id == "chat_test_1"

    await session.stop(reason="Stream completed")
    assert session.status == StreamStatus.ENDED
    assert session.is_active is False


@pytest.mark.asyncio
async def test_stream_session_summary_safe_telemetry():
    """Verify StreamSessionSummary contains all required safe telemetry without raw secrets."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream(stream_id="STREAM_TEST_2", title="Music Stream", concurrent_viewers=320)

    session = StreamSession(stream_id="STREAM_TEST_2", api_client=fake_api)
    await session.start()

    summary = session.to_summary()
    assert summary.stream_id == "STREAM_TEST_2"
    assert summary.video_id == "STREAM_TEST_2"
    assert summary.title == "Music Stream"
    assert summary.status == StreamStatus.LIVE
    assert summary.connection_status == "LIVE"
    assert summary.concurrent_viewers == 320
    assert summary.connected_at is not None
    assert summary.uptime_seconds >= 0.0

    # Ensure zero raw keys in dumped model
    dumped = summary.model_dump()
    assert "raw_key" not in dumped
    assert "api_key" not in dumped

    await session.stop()
