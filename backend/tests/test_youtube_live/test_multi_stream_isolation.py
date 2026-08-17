"""
Tests for 4-Stream Simultaneous Execution & Isolation in GODDESS AI 2.0.
"""

import asyncio
import pytest
from app.core.events import event_bus
from app.services.youtube.stream_manager import StreamManager
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


@pytest.mark.asyncio
async def test_four_simultaneous_streams_isolation():
    """Verify STREAM_A, STREAM_B, STREAM_C, STREAM_D run simultaneously without cross-talk."""
    fake_api = FakeYouTubeProvider()
    fake_api.register_stream("STREAM_A", title="Stream Alpha", live_chat_id="chat_a")
    fake_api.register_stream("STREAM_B", title="Stream Beta", live_chat_id="chat_b")
    fake_api.register_stream("STREAM_C", title="Stream Gamma", live_chat_id="chat_c")
    fake_api.register_stream("STREAM_D", title="Stream Delta", live_chat_id="chat_d")

    mgr = StreamManager(max_concurrent_streams=4, api_client=fake_api)

    # Queue unique messages to respective chats
    fake_api.queue_chat_message("chat_a", "Alice", "Hello A", message_id="msg_a")
    fake_api.queue_chat_message("chat_b", "Bob", "Hello B", message_id="msg_b")
    fake_api.queue_chat_message("chat_c", "Charlie", "Hello C", message_id="msg_c")
    fake_api.queue_chat_message("chat_d", "Dana", "Hello D", message_id="msg_d")

    collected_by_stream = {"STREAM_A": [], "STREAM_B": [], "STREAM_C": [], "STREAM_D": []}

    async def chat_listener(data):
        sid = data.get("stream_id")
        if sid in collected_by_stream:
            collected_by_stream[sid].append(data["message"]["message_text"])

    event_bus.subscribe("CHAT_MESSAGE", chat_listener)

    # Start all 4 sessions
    s_a = await mgr.create_session("STREAM_A", auto_start=True)
    s_b = await mgr.create_session("STREAM_B", auto_start=True)
    s_c = await mgr.create_session("STREAM_C", auto_start=True)
    s_d = await mgr.create_session("STREAM_D", auto_start=True)

    assert mgr.active_stream_count == 4

    await asyncio.sleep(0.2)

    # Stop all sessions
    await s_a.stop()
    await s_b.stop()
    await s_c.stop()
    await s_d.stop()

    assert collected_by_stream["STREAM_A"] == ["Hello A"]
    assert collected_by_stream["STREAM_B"] == ["Hello B"]
    assert collected_by_stream["STREAM_C"] == ["Hello C"]
    assert collected_by_stream["STREAM_D"] == ["Hello D"]
