"""
Tests for AI Duplicate Response Prevention in GODDESS AI 2.0.
"""

from app.services.cohost.deduplication import ResponseDeduplicator


def test_duplicate_response_prevention():
    """Verify duplicate response text is detected and blocked within cooldown window."""
    dedup = ResponseDeduplicator()

    is_dup1 = dedup.is_duplicate("STREAM_DEDUP", "Thank you for watching the stream!")
    assert is_dup1 is False

    dedup.record_response("STREAM_DEDUP", "Thank you for watching the stream!")

    # Immediate repetition must be flagged as duplicate
    is_dup2 = dedup.is_duplicate("STREAM_DEDUP", "Thank you for watching the stream!")
    assert is_dup2 is True
