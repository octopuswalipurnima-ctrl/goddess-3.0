"""
Tests for Per-Viewer Context Bounds (Max 5) in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.context import StreamContext
from app.services.cohost.models import CoHostMessage


def test_viewer_context_limit_strictly_capped_at_five():
    """Verify viewer history does not exceed 5 messages."""
    ctx = StreamContext(stream_id="STREAM_A", max_user_messages=5)

    for i in range(10):
        msg = CoHostMessage(
            stream_id="STREAM_A",
            message_id=f"m_{i}",
            author_id="user_alice",
            author_name="Alice",
            message_text=f"Message {i}",
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.user_history["user_alice"]) == 5
    # Oldest retained message should be Message 5
    assert ctx.user_history["user_alice"][0][0] == "Message 5"
