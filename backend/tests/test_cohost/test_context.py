"""
Tests for CoHostContextManager, Bounded Memory, and Multi-Stream Isolation.
"""

import pytest
from app.services.cohost.context import CoHostContextManager
from app.services.cohost.models import CoHostMessage


def test_context_manager_bounded_stream_history():
    """
    CRITICAL: Verify stream history is strictly bounded to 20 messages.
    """
    mgr = CoHostContextManager()
    ctx = mgr.get_context("stream_test", max_stream_messages=20)

    for i in range(30):
        msg = CoHostMessage(
            stream_id="stream_test",
            message_id=f"m_{i}",
            author_id=f"user_{i % 5}",
            author_name=f"User{i % 5}",
            message_text=f"Chat message number {i}",
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.stream_history) == 20


def test_context_manager_bounded_user_history():
    """
    CRITICAL: Verify user interaction history is strictly bounded to 5 messages.
    """
    mgr = CoHostContextManager()
    ctx = mgr.get_context("stream_test", max_user_messages=5)

    for i in range(10):
        msg = CoHostMessage(
            stream_id="stream_test",
            message_id=f"m_u_{i}",
            author_id="frequent_user",
            author_name="FrequentViewer",
            message_text=f"User msg {i}",
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.user_history["frequent_user"]) == 5


def test_context_manager_multi_stream_isolation():
    """Verify Stream A context never leaks into Stream B."""
    mgr = CoHostContextManager()
    ctx_a = mgr.get_context("stream_A")
    ctx_b = mgr.get_context("stream_B")

    msg_a = CoHostMessage(
        stream_id="stream_A",
        message_id="msg_a",
        author_id="user_a",
        author_name="Alice",
        message_text="Hello from Stream A",
    )
    ctx_a.add_viewer_message(msg_a)

    assert len(ctx_a.stream_history) == 1
    assert len(ctx_b.stream_history) == 0
