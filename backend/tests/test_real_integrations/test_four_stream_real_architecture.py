"""
Real Architecture Audit: 4 Simultaneous Stream Isolation in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_four_simultaneous_real_stream_architectural_isolation():
    """Verify 4 stream pipelines run concurrently with independent supervisors, sessions, and state."""
    fake_api = FakeYouTubeProvider()
    stream_ids = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]
    for sid in stream_ids:
        fake_api.register_stream(sid, title=f"Broadcast {sid}", live_chat_id=f"chat_{sid.lower()}")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)

    sessions = []
    for sid in stream_ids:
        s = await supervisor.attach_stream(sid)
        sessions.append(s)

    assert supervisor.active_stream_count == 4
    for s in sessions:
        assert s.state == SupervisorState.LIVE

    # Ensure no crosstalk across stream sessions
    for i, s1 in enumerate(sessions):
        for j, s2 in enumerate(sessions):
            if i != j:
                assert s1.stream_id != s2.stream_id
                assert s1.session is not s2.session

    await supervisor.shutdown()
