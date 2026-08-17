"""
Tests for Production StreamSupervisor in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.exceptions import DuplicateStreamError, MaxStreamsReachedError
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_stream_supervisor_attach_and_detach():
    """Verify StreamSupervisor attaches a stream, transitions to LIVE, and detaches cleanly."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream("STREAM_SUP_1", title="Gaming Live", live_chat_id="chat_sup_1")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)
    session = await supervisor.attach_stream("STREAM_SUP_1", auto_start=True)

    assert session.state == SupervisorState.LIVE
    assert supervisor.active_stream_count == 1

    summary = session.to_summary()
    assert summary.stream_id == "STREAM_SUP_1"
    assert summary.state == SupervisorState.LIVE
    assert summary.title == "Gaming Live"

    # Detach stream
    detached = await supervisor.detach_stream("STREAM_SUP_1")
    assert detached is True
    assert session.state == SupervisorState.ENDED
    assert supervisor.active_stream_count == 0


@pytest.mark.asyncio
async def test_stream_supervisor_duplicate_and_capacity_limits():
    """Verify duplicate stream attach and capacity limits (max 4) are strictly enforced."""
    fake_api = FakeYouTubeProvider()
    for i in range(1, 6):
        fake_api.register_stream(f"STREAM_CAP_{i}", live_chat_id=f"chat_{i}")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)

    # Attach 4 streams
    for i in range(1, 5):
        await supervisor.attach_stream(f"STREAM_CAP_{i}", auto_start=True)

    assert supervisor.active_stream_count == 4

    # Duplicate attach must raise DuplicateStreamError
    with pytest.raises(DuplicateStreamError):
        await supervisor.attach_stream("STREAM_CAP_1")

    # 5th attach must raise MaxStreamsReachedError
    with pytest.raises(MaxStreamsReachedError):
        await supervisor.attach_stream("STREAM_CAP_5")

    # Teardown
    await supervisor.shutdown()
