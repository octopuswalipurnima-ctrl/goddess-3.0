"""
Tests for Conversation Continuity across Context Windows in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.context import CoHostContextManager
from app.services.cohost.models import CoHostMessage


def test_conversation_continuity_preserves_dialogue():
    """Verify viewer follow-up questions can resolve against recent context."""
    ctx_mgr = CoHostContextManager()
    ctx = ctx_mgr.get_context("STREAM_A")

    msg1 = CoHostMessage(
        stream_id="STREAM_A",
        message_id="m1",
        author_id="user_1",
        author_name="Alice",
        message_text="Which weapon are you using?",
    )
    ctx.add_viewer_message(msg1)
    ctx.add_cohost_response("I'm using the Phantom rifle right now!", persona_name="Goddess")

    msg2 = CoHostMessage(
        stream_id="STREAM_A",
        message_id="m2",
        author_id="user_1",
        author_name="Alice",
        message_text="And what skin is on it?",
    )
    ctx.add_viewer_message(msg2)

    formatted = ctx.get_formatted_context(current_author_id="user_1")
    assert "Phantom rifle" in formatted
    assert "Which weapon" in formatted
