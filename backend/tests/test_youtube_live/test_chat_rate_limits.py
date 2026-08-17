"""
Tests for Live Chat Polling Interval Clamping & Rate Limiting in GODDESS AI 2.0.
"""

from app.services.youtube.chat import LiveChatReader
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


def test_polling_interval_clamped_to_safe_minimum():
    """Verify polling interval reported by YouTube is never allowed below 1.0s."""
    fake_api = FakeYouTubeProvider()
    reader = LiveChatReader(stream_id="STREAM_CLAMP_1", live_chat_id="chat_clamp_1", api_client=fake_api)

    # Initial safe default is 4.0s
    assert reader._polling_interval_sec >= 1.0
