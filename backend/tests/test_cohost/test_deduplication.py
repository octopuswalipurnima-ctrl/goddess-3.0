"""
Tests for ResponseDeduplicator.
"""

import pytest
from app.services.cohost.deduplication import ResponseDeduplicator


def test_response_deduplication_exact_and_normalized():
    """Verify duplicate and normalized identical replies are blocked."""
    dedup = ResponseDeduplicator()

    # Record first response
    dedup.record_response("stream_1", "Welcome to the live stream! Hope you enjoy.")

    # Check same response
    assert dedup.is_duplicate("stream_1", "Welcome to the live stream! Hope you enjoy.") is True
    # Check normalized response (different casing / punctuation)
    assert dedup.is_duplicate("stream_1", "welcome to the live stream hope you enjoy") is True

    # Different response should not be duplicate
    assert dedup.is_duplicate("stream_1", "We are currently playing BGMI!") is False


def test_response_deduplication_stream_isolation():
    """Verify deduplication history is isolated per stream."""
    dedup = ResponseDeduplicator()

    dedup.record_response("stream_A", "Good luck in the next game!")

    # Same response on Stream B should NOT be marked as duplicate
    assert dedup.is_duplicate("stream_B", "Good luck in the next game!") is False
