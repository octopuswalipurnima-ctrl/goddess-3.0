"""
Tests for Central StreamManager, Concurrency Limit (4 Streams), and Session Isolation.
"""

import pytest
from app.core.events import event_bus
from app.services.youtube.exceptions import DuplicateStreamError, MaxStreamsReachedError
from app.services.youtube.models import LiveStreamInfo, StreamStatus
from app.services.youtube.stream_manager import StreamManager


class MockManagerAPIClient:
    """Mock client returning custom stream details."""

    async def get_live_stream_details(self, stream_id: str):
        if stream_id == "failing_stream":
            raise ConnectionError("Simulated network failure on stream A")
        return LiveStreamInfo(
            stream_id=stream_id,
            channel_id=f"channel_{stream_id}",
            title=f"Live Stream {stream_id}",
            status=StreamStatus.LIVE,
            concurrent_viewers=200,
            live_chat_id=f"chat_{stream_id}",
        )

    async def get_live_chat_messages(self, live_chat_id: str, page_token: str = None):
        return [], None, 1000


@pytest.mark.asyncio
async def test_stream_manager_concurrency_limit():
    """Verify enforcement of maximum concurrent streams (default: 4)."""
    mock_client = MockManagerAPIClient()
    mgr = StreamManager(max_concurrent_streams=4, api_client=mock_client)

    # Add 4 simultaneous streams
    s1 = await mgr.create_session("stream_A", auto_start=True)
    s2 = await mgr.create_session("stream_B", auto_start=True)
    s3 = await mgr.create_session("stream_C", auto_start=True)
    s4 = await mgr.create_session("stream_D", auto_start=True)

    assert mgr.active_stream_count == 4
    assert len(mgr.list_sessions()) == 4

    # Attempting to add a 5th stream must raise MaxStreamsReachedError
    with pytest.raises(MaxStreamsReachedError):
        await mgr.create_session("stream_E", auto_start=True)

    # Clean up
    await mgr.stop_all()
    assert mgr.active_stream_count == 0


@pytest.mark.asyncio
async def test_duplicate_stream_protection():
    """Verify that creating a duplicate session for an active stream is rejected."""
    mock_client = MockManagerAPIClient()
    mgr = StreamManager(max_concurrent_streams=4, api_client=mock_client)

    await mgr.create_session("stream_101", auto_start=True)

    with pytest.raises(DuplicateStreamError):
        await mgr.create_session("stream_101", auto_start=True)

    await mgr.stop_all()


@pytest.mark.asyncio
async def test_stream_session_failure_isolation():
    """
    CRITICAL: Verify that if Stream A encounters a fatal error,
    concurrent Streams B, C, and D remain LIVE and unaffected.
    """
    mock_client = MockManagerAPIClient()
    mgr = StreamManager(max_concurrent_streams=4, api_client=mock_client)

    # Stream B and C are healthy
    sb = await mgr.create_session("stream_B", auto_start=True)
    sc = await mgr.create_session("stream_C", auto_start=True)
    assert sb.status == StreamStatus.LIVE
    assert sc.status == StreamStatus.LIVE

    # Stream A fails during start
    sa = await mgr.create_session("failing_stream", auto_start=True)
    assert sa.status == StreamStatus.FAILED

    # Streams B and C must still be completely healthy and LIVE
    assert sb.status == StreamStatus.LIVE
    assert sc.status == StreamStatus.LIVE
    assert mgr.get_session("stream_B").is_active is True
    assert mgr.get_session("stream_C").is_active is True

    await mgr.stop_all()
