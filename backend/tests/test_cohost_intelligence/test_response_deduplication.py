"""
Tests for Response Deduplication in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.deduplication import ResponseDeduplicator


def test_response_exact_deduplication():
    """Verify duplicate responses within recent window are blocked."""
    dedup = ResponseDeduplicator(history_size=30)

    dedup.record_response("STREAM_A", "Welcome to the stream Alice!")

    is_dup_exact = dedup.is_duplicate("STREAM_A", "Welcome to the stream Alice!")
    assert is_dup_exact is True

    is_dup_case = dedup.is_duplicate("STREAM_A", "welcome to the stream alice")
    assert is_dup_case is True

    is_dup_diff = dedup.is_duplicate("STREAM_A", "Glad to see you Bob!")
    assert is_dup_diff is False
