"""
Tests for 4-Stream Context Isolation in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.context import CoHostContextManager
from app.services.cohost.models import CoHostMessage


def test_four_stream_context_memory_isolation():
    """Verify messages in STREAM_A never appear in context for STREAM_B, C, or D."""
    ctx_mgr = CoHostContextManager()

    ctx_a = ctx_mgr.get_context("STREAM_A")
    ctx_b = ctx_mgr.get_context("STREAM_B")
    ctx_c = ctx_mgr.get_context("STREAM_C")
    ctx_d = ctx_mgr.get_context("STREAM_D")

    msg_a = CoHostMessage(
        stream_id="STREAM_A",
        message_id="msg_a_secret",
        author_id="user_a",
        author_name="Alice",
        message_text="Secret chat on Stream A only",
    )
    ctx_a.add_viewer_message(msg_a)

    assert "Secret chat" in ctx_a.get_formatted_context()
    assert "Secret chat" not in ctx_b.get_formatted_context()
    assert "Secret chat" not in ctx_c.get_formatted_context()
    assert "Secret chat" not in ctx_d.get_formatted_context()
