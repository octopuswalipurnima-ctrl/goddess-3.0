"""
Tests for Zero Cross-Stream Cooldown Contamination in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.cooldowns import CoHostCooldownTracker


def test_cooldowns_are_strictly_isolated_by_stream():
    """Verify triggering a user cooldown on STREAM_A does not lock out that user on STREAM_B."""
    tracker = CoHostCooldownTracker()

    # User replies on Stream A
    tracker.record_response("STREAM_A", "user_alice")

    # User should be blocked on Stream A
    allowed_a, _ = tracker.check_cooldowns("STREAM_A", "user_alice", user_cooldown=30.0)
    assert allowed_a is False

    # User MUST be allowed on Stream B
    allowed_b, _ = tracker.check_cooldowns("STREAM_B", "user_alice", user_cooldown=30.0)
    assert allowed_b is True
