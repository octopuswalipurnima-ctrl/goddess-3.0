"""
Tests for CoHost Cooldown Policies in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.cooldowns import CoHostCooldownTracker


def test_cooldown_policy_enforces_user_and_global_limits():
    """Verify cooldown tracker blocks rapid successive replies."""
    tracker = CoHostCooldownTracker()

    # Initial check passes
    allowed, _ = tracker.check_cooldowns("STREAM_A", "user_1", global_cooldown=5.0, user_cooldown=30.0)
    assert allowed is True

    # Record response
    tracker.record_response("STREAM_A", "user_1")

    # Immediate follow-up from same user fails user cooldown (setting global_cooldown=0 to isolate user check)
    allowed_user, reason = tracker.check_cooldowns("STREAM_A", "user_1", global_cooldown=0.0, user_cooldown=30.0)
    assert allowed_user is False
    assert "response cooldown active" in reason

    # Immediate message from different user fails global cooldown
    allowed_global, reason_g = tracker.check_cooldowns("STREAM_A", "user_2", global_cooldown=5.0, user_cooldown=0.0)
    assert allowed_global is False
    assert "Global response cooldown active" in reason_g
