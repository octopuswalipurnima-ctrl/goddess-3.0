"""
Tests for Stream Context Bounds (Max 20) in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.context import StreamContext
from app.services.cohost.models import CoHostMessage


def test_stream_context_limit_strictly_capped_at_twenty():
    """Verify stream history does not exceed 20 messages."""
    ctx = StreamContext(stream_id="STREAM_A", max_stream_messages=20)

    for i in range(35):
        msg = CoHostMessage(
            stream_id="STREAM_A",
            message_id=f"msg_{i}",
            author_id=f"user_{i}",
            author_name=f"Viewer_{i}",
            message_text=f"Chat line {i}",
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.stream_history) == 20
    assert ctx.stream_history[0][2] == "Chat line 15"
