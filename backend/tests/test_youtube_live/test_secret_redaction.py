"""
Tests for Zero Secret Exposure in YouTube Live Module of GODDESS AI 2.0.
"""

from app.core.provider_errors import sanitize_error_message
from app.services.youtube.models import ChatMessageEvent, StreamSessionSummary, StreamStatus


def test_no_secrets_in_chat_message_event():
    """Verify ChatMessageEvent schema never includes secret fields."""
    event = ChatMessageEvent(
        event_id="evt_001",
        stream_id="STREAM_A",
        message_id="msg_001",
        author_id="user_123",
        author_display_name="User123",
        message_text="Standard chat text",
        metadata={"user_type": "viewer"},
    )
    dumped = event.model_dump()
    assert "raw_key" not in dumped
    assert "api_key" not in dumped
    assert "token" not in dumped


def test_no_secrets_in_session_summary():
    """Verify StreamSessionSummary schema contains zero raw API keys."""
    summary = StreamSessionSummary(
        stream_id="STREAM_A",
        status=StreamStatus.LIVE,
    )
    dumped = summary.model_dump()
    assert "raw_key" not in dumped
    assert "api_key" not in dumped
