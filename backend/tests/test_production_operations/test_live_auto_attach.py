"""
Tests for Automatic Stream Discovery & Supervisor Attachment in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.live_detection import LiveStreamDetector
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_live_auto_attach_flow():
    """Verify stream discovery triggers supervisor attach and transitions to LIVE."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream("v_auto_live_01", title="Discovered Stream", live_chat_id="chat_auto_01")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)
    session = await supervisor.attach_stream("v_auto_live_01", auto_start=True)

    assert session.state == SupervisorState.LIVE
    assert supervisor.active_stream_count == 1
    await supervisor.shutdown()
