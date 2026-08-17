"""
Tests for CoHostCooldownTracker, Global Cooldowns (5s), Per-User Cooldowns (30s), and Rate Limits.
"""

import time
import pytest
from app.services.cohost.cooldowns import CoHostCooldownTracker


def test_cooldown_tracker_global_and_user_cooldowns():
    """Verify global (5s) and per-user (30s) response spacing."""
    tracker = CoHostCooldownTracker()

    # Initial check should pass
    allowed, _ = tracker.check_cooldowns(
        stream_id="s1",
        author_id="u1",
        global_cooldown=5.0,
        user_cooldown=30.0,
    )
    assert allowed is True

    # Record response
    tracker.record_response("s1", "u1")

    # Immediate second request from same user should fail per-user (and global) cooldown
    allowed_same, reason_same = tracker.check_cooldowns(
        stream_id="s1",
        author_id="u1",
        global_cooldown=5.0,
        user_cooldown=30.0,
    )
    assert allowed_same is False
    assert "cooldown active" in reason_same

    # Immediate request from different user should fail global cooldown
    allowed_diff, reason_diff = tracker.check_cooldowns(
        stream_id="s1",
        author_id="u2",
        global_cooldown=5.0,
        user_cooldown=30.0,
    )
    assert allowed_diff is False
    assert "Global response cooldown active" in reason_diff


def test_cooldown_tracker_stream_rate_limit():
    """Verify stream cap of max 12 responses per minute."""
    tracker = CoHostCooldownTracker()

    # Fill rate limit with 12 distinct users
    for i in range(12):
        tracker.record_response("s_rate", f"user_{i}")

    # 13th response in same minute should be rejected
    allowed, reason = tracker.check_cooldowns(
        stream_id="s_rate",
        author_id="user_13",
        global_cooldown=0.0,  # Zero out cooldown to isolate rate limit test
        user_cooldown=0.0,
        max_per_minute=12,
    )
    assert allowed is False
    assert "rate limit reached" in reason
