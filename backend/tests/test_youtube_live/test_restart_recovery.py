"""
Tests for Restart Recovery & State Cleanliness in GODDESS AI 2.0.
"""

from app.services.youtube.models import StreamSessionSummary, StreamStatus
from app.services.youtube.stream_manager import StreamManager
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


def test_clean_session_state_on_initialization():
    """Verify new StreamManager initializes cleanly with 0 stale active streams."""
    fake_api = FakeYouTubeProvider()
    mgr = StreamManager(max_concurrent_streams=4, api_client=fake_api)

    assert mgr.active_stream_count == 0
    assert mgr.total_stream_count == 0
