"""
Tests for Zero Cross-Stream State Contamination in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.stream_supervisor import StreamSupervisor, SupervisorState
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_stream_crash_isolation_in_supervisor():
    """Verify failure/crash on STREAM_A does not disrupt STREAM_B, STREAM_C, or STREAM_D."""
    fake_api = FakeYouTubeProvider()
    for sid in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        fake_api.register_stream(sid, title=f"Title {sid}", live_chat_id=f"chat_{sid.lower()}")

    supervisor = StreamSupervisor(max_concurrent_streams=4, api_client=fake_api)

    s_a = await supervisor.attach_stream("STREAM_A")
    s_b = await supervisor.attach_stream("STREAM_B")
    s_c = await supervisor.attach_stream("STREAM_C")
    s_d = await supervisor.attach_stream("STREAM_D")

    # Terminate / Fail STREAM_A
    await s_a.stop(reason="Crash simulation")
    assert s_a.state == SupervisorState.ENDED

    # B, C, D must remain strictly LIVE
    assert s_b.state == SupervisorState.LIVE
    assert s_c.state == SupervisorState.LIVE
    assert s_d.state == SupervisorState.LIVE
    assert supervisor.active_stream_count == 3

    await supervisor.shutdown()
