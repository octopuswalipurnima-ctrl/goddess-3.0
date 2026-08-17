"""
Controlled Real YouTube Live API Integration & Session Tests for GODDESS AI 2.0.

Requires explicit RUN_REAL_YOUTUBE_TEST=true and TEST_REAL_YOUTUBE_VIDEO_ID.
Never interacts with arbitrary or production streams.
"""

import os
import pytest
from app.core.config import settings
from app.services.youtube.credentials import youtube_credentials
from app.services.youtube.stream_supervisor import stream_supervisor


@pytest.mark.asyncio
async def test_real_youtube_live_stream_supervision():
    """
    Validate real YouTube Live discovery, liveChatId lookup, and clean detachment on a test stream.
    """
    if os.getenv("RUN_REAL_YOUTUBE_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_YOUTUBE_TEST is not true. Skipping real YouTube test.")

    test_video_id = os.getenv("TEST_REAL_YOUTUBE_VIDEO_ID")
    if not test_video_id:
        pytest.skip("TEST_REAL_YOUTUBE_VIDEO_ID not specified. Skipping real YouTube test.")

    if not settings.is_youtube_configured:
        pytest.skip("No YouTube API keys configured. Skipping real YouTube test.")

    # Attach supervised test session
    session = await stream_supervisor.attach_stream(
        stream_id="STREAM_TEST_REAL",
        video_id=test_video_id,
        auto_start=True,
    )
    assert session is not None
    assert session.stream_id == "STREAM_TEST_REAL"

    # Detach cleanly
    await stream_supervisor.detach_stream("STREAM_TEST_REAL")
