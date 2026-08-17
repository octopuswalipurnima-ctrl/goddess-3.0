"""
Tests for Multi-Stream AI Context & State Isolation in GODDESS AI 2.0.
"""

from app.services.cohost.context import CoHostContextManager
from app.services.cohost.models import CoHostMessage


def test_four_stream_ai_context_isolation():
    """Verify STREAM_A, STREAM_B, STREAM_C, and STREAM_D contexts are completely isolated."""
    ctx_mgr = CoHostContextManager()

    streams = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]
    for s in streams:
        ctx = ctx_mgr.get_context(s)
        msg = CoHostMessage(
            message_id=f"msg_{s}",
            stream_id=s,
            author_id=f"user_{s}",
            author_name=f"Viewer_{s}",
            message_text=f"Unique message for {s}",
        )
        ctx.add_viewer_message(msg)

    # Verify context isolation
    for s in streams:
        formatted = ctx_mgr.get_context(s).get_formatted_context()
        assert f"Unique message for {s}" in formatted
        # Other streams must NOT appear in this stream's context
        for other in streams:
            if other != s:
                assert f"Unique message for {other}" not in formatted
