"""
Tests for Bounded AI Context & Memory in GODDESS AI 2.0.
"""

from app.services.cohost.context import CoHostContextManager, StreamContext
from app.services.cohost.models import CoHostMessage


def test_stream_context_bounded_to_20_messages():
    """Verify StreamContext strictly limits stream conversation history to 20 messages."""
    ctx = StreamContext("STREAM_CTX_TEST", max_stream_messages=20)

    for i in range(25):
        msg = CoHostMessage(
            message_id=f"m_{i}",
            stream_id="STREAM_CTX_TEST",
            author_id=f"u_{i}",
            author_name=f"User{i}",
            message_text=f"Hello message {i}",
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.stream_history) == 20
    # Oldest message should be m_5
    assert ctx.stream_history[0][2] == "Hello message 5"
    assert ctx.stream_history[-1][2] == "Hello message 24"


def test_viewer_context_bounded_to_5_messages():
    """Verify StreamContext strictly limits per-viewer history to 5 messages."""
    ctx = StreamContext("STREAM_USER_CTX", max_user_messages=5)

    for i in range(10):
        msg = CoHostMessage(
            message_id=f"m_u_{i}",
            stream_id="STREAM_USER_CTX",
            author_id="viewer_frequent",
            author_name="FrequentViewer",
            message_text=f"Question {i}",
        )
        ctx.add_viewer_message(msg)

    user_hist = ctx.user_history["viewer_frequent"]
    assert len(user_hist) == 5
    assert user_hist[0][0] == "Question 5"
    assert user_hist[-1][0] == "Question 9"
