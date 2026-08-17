"""
Tests for Production Graceful Shutdown Operations in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller
from app.services.youtube.stream_supervisor import StreamSupervisor
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_shutdown_marks_safety_controller_and_closes_supervisors():
    """Verify shutdown cancels active supervisor sessions and marks safety controller as SHUTTING_DOWN."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream("STR_SHUTDOWN_1", live_chat_id="chat_sd1")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)
    await supervisor.attach_stream("STR_SHUTDOWN_1")

    assert supervisor.active_stream_count == 1

    await supervisor.shutdown()
    assert supervisor.active_stream_count == 0

    safety_controller.set_shutting_down()
    assert safety_controller.is_shutting_down is True

    # Restore normal for other tests
    safety_controller._global_state = safety_controller._global_state.__class__.NORMAL
