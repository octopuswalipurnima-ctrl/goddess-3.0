"""
Tests for ViewerInteractionModule: interaction tracking, LRU memory bounds, and top participants.
"""

import pytest

from app.modules.models import StreamModuleConfig
from app.modules.viewer_interaction.module import ViewerInteractionModule


@pytest.mark.asyncio
async def test_viewer_interaction_module_bounded_tracking():
    # Module with max 2 records for testing bounded memory
    mod = ViewerInteractionModule(max_records_per_stream=2)
    mod.update_stream_config("stream_1", StreamModuleConfig(enabled=True))

    # User 1 sends message
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m1",
            "author_id": "u1",
            "author_name": "Alice",
            "message_text": "First msg",
        },
    )
    # User 2 sends message
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m2",
            "author_id": "u2",
            "author_name": "Bob",
            "message_text": "Second msg",
        },
    )
    # User 1 sends another
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m3",
            "author_id": "u1",
            "author_name": "Alice",
            "message_text": "Third msg",
        },
    )

    stats_u1 = mod.get_viewer_stats("stream_1", "u1")
    assert stats_u1 is not None
    assert stats_u1["message_count"] == 2

    # User 3 sends message (evicts LRU: u2)
    await mod.handle_event(
        "CHAT_MESSAGE",
        {
            "stream_id": "stream_1",
            "message_id": "m4",
            "author_id": "u3",
            "author_name": "Charlie",
            "message_text": "Fourth msg",
        },
    )

    assert mod.get_viewer_stats("stream_1", "u2") is None  # Evicted
    assert mod.get_viewer_stats("stream_1", "u3") is not None
    assert mod.get_viewer_stats("stream_1", "u1") is not None
