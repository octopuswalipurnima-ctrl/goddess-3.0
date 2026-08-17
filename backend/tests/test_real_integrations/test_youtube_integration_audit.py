"""
Real Service Integration Audit: YouTube Data & Live Streaming API for GODDESS AI 2.0.
"""

import os
import pytest
from app.services.youtube.client import youtube_client
from app.services.youtube.credentials import youtube_credentials


def test_youtube_credential_pool_loading():
    """Verify YouTube credentials pool loads from environment safely with zero secret exposure."""
    summary = youtube_credentials.get_health_summary()
    assert isinstance(summary, list)
    assert len(summary) == 4
    for slot in summary:
        assert hasattr(slot, "key_id")
        assert hasattr(slot, "state")
    assert "AIzaSy" not in str(summary)


@pytest.mark.asyncio
async def test_real_youtube_api_when_opted_in():
    """
    Real YouTube API live integration check.
    Only runs when RUN_REAL_YOUTUBE_TEST=true is explicitly configured in environment.
    """
    if os.getenv("RUN_REAL_YOUTUBE_TEST", "").lower() != "true":
        pytest.skip("RUN_REAL_YOUTUBE_TEST is not true. Skipping real YouTube API call.")

    stream_id = os.getenv("TEST_YOUTUBE_STREAM_ID")
    if not stream_id:
        pytest.skip("TEST_YOUTUBE_STREAM_ID not provided. Skipping real YouTube API call.")

    details = await youtube_client.get_live_stream_details(stream_id)
    assert details is not None
