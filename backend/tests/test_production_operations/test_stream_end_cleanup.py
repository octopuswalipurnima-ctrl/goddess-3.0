"""
Tests for Stream Termination Cleanup in GODDESS AI 2.0.
"""

import pytest
from app.core.events import event_bus
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_stream_ended_triggers_supervisor_cleanup():
    """Verify STREAM_ENDED event transitions supervisor session to ENDED and decrements active count."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream("STREAM_END_1", live_chat_id="chat_end_1")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)
    session = await supervisor.attach_stream("STREAM_END_1", auto_start=True)

    assert supervisor.active_stream_count == 1
    assert session.state == SupervisorState.LIVE

    # Publish STREAM_ENDED
    await event_bus.publish("STREAM_ENDED", {"stream_id": "STREAM_END_1", "reason": "Broadcast finished"})

    assert session.state == SupervisorState.ENDED
    assert supervisor.active_stream_count == 0
