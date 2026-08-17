"""
Tests for 4 Simultaneous Supervised Streams in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_four_simultaneous_supervised_streams():
    """Verify STREAM_A, STREAM_B, STREAM_C, STREAM_D run simultaneously under supervision."""
    fake_api = FakeYouTubeProvider()
    for sid in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        fake_api.register_stream(sid, title=f"Title {sid}", live_chat_id=f"chat_{sid.lower()}")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)

    s_a = await supervisor.attach_stream("STREAM_A")
    s_b = await supervisor.attach_stream("STREAM_B")
    s_c = await supervisor.attach_stream("STREAM_C")
    s_d = await supervisor.attach_stream("STREAM_D")

    assert supervisor.active_stream_count == 4
    assert s_a.state == SupervisorState.LIVE
    assert s_b.state == SupervisorState.LIVE
    assert s_c.state == SupervisorState.LIVE
    assert s_d.state == SupervisorState.LIVE

    summaries = supervisor.list_supervisor_sessions()
    assert len(summaries) == 4
    stream_ids = [s.stream_id for s in summaries]
    assert "STREAM_A" in stream_ids
    assert "STREAM_B" in stream_ids
    assert "STREAM_C" in stream_ids
    assert "STREAM_D" in stream_ids

    await supervisor.shutdown()
    assert supervisor.active_stream_count == 0
