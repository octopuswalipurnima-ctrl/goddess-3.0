"""
Tests for StreamStatsModule: per-stream metrics aggregation and isolation.
"""

import pytest

from app.modules.stream_stats.module import StreamStatsModule


@pytest.mark.asyncio
async def test_stream_stats_module_metrics_and_isolation():
    mod = StreamStatsModule()

    # Dispatch events to stream_A
    await mod.handle_event("CHAT_MESSAGE", {"stream_id": "stream_A"})
    await mod.handle_event("CHAT_MESSAGE", {"stream_id": "stream_A"})
    await mod.handle_event("MODERATION_ACTION_EXECUTED", {"stream_id": "stream_A"})
    await mod.handle_event("COHOST_RESPONSE_SENT", {"stream_id": "stream_A"})

    # Dispatch event to stream_B
    await mod.handle_event("CHAT_MESSAGE", {"stream_id": "stream_B"})

    metrics_a = mod.get_stream_metrics("stream_A")
    assert metrics_a["messages_count"] == 2
    assert metrics_a["moderation_actions_count"] == 1
    assert metrics_a["cohost_responses_count"] == 1
    assert metrics_a["module_events_count"] == 4

    metrics_b = mod.get_stream_metrics("stream_B")
    assert metrics_b["messages_count"] == 1
    assert metrics_b["moderation_actions_count"] == 0
    assert metrics_b["cohost_responses_count"] == 0
    assert metrics_b["module_events_count"] == 1
