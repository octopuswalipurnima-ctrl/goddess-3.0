"""
Tests for ActionPolicy Gate, Kill Switch, Safe Mode, Exemptions, Cooldowns, and Automatic Circuit Breaker.
"""

import time
import pytest
from app.services.moderation.models import (
    ActionSeverity,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
    ModerationSource,
    StreamModerationConfig,
    UserRole,
)
from app.services.moderation.policy import ActionPolicy


def test_policy_owner_and_moderator_exemption():
    """Verify channel owner and moderator are exempt from automated actions."""
    policy = ActionPolicy()
    config = StreamModerationConfig(owner_exempt=True, moderator_exempt=True)

    owner_dec = ModerationDecision(
        message_id="m_owner",
        stream_id="stream_1",
        author_id="owner_1",
        author_name="Streamer",
        user_role=UserRole.OWNER,
        category=ModerationCategory.SPAM,
        confidence=0.99,
        severity=ActionSeverity.HIGH,
        recommended_action=ModerationAction.DELETE,
    )

    approved, effective_act, reason = policy.evaluate_action(owner_dec, config)
    assert approved is False
    assert effective_act == ModerationAction.LOG
    assert "owner is exempt" in reason.lower()


def test_policy_emergency_kill_switch():
    """Verify emergency kill switch immediately stops all automated actions."""
    policy = ActionPolicy()
    config = StreamModerationConfig(kill_switch=True)

    dec = ModerationDecision(
        message_id="m_spam",
        stream_id="stream_1",
        author_id="spammer_1",
        author_name="BadUser",
        user_role=UserRole.USER,
        category=ModerationCategory.MALICIOUS_LINK,
        confidence=0.99,
        severity=ActionSeverity.HIGH,
        recommended_action=ModerationAction.DELETE,
    )

    approved, effective_act, reason = policy.evaluate_action(dec, config)
    assert approved is False
    assert effective_act == ModerationAction.LOG
    assert "Kill Switch is ACTIVE" in reason


def test_policy_automatic_circuit_breaker_trips_and_resets():
    """
    CRITICAL REQUIREMENT: An action burst triggers the automatic circuit breaker,
    blocking subsequent automated actions until explicitly reset.
    """
    policy = ActionPolicy()
    config = StreamModerationConfig(
        circuit_breaker_action_threshold=4,
        circuit_breaker_window_seconds=10.0,
        cooldown_seconds_per_user=0,  # Disable per-user cooldown to test global stream burst
    )

    # Trigger 3 rapid actions (under threshold)
    for i in range(3):
        dec = ModerationDecision(
            message_id=f"m_burst_{i}",
            stream_id="stream_cb",
            author_id=f"user_burst_{i}",
            author_name=f"UserBurst{i}",
            category=ModerationCategory.SPAM,
            confidence=0.95,
            recommended_action=ModerationAction.DELETE,
        )
        approved, _, _ = policy.evaluate_action(dec, config)
        assert approved is True

    # 4th action hits threshold and MUST trip circuit breaker
    dec4 = ModerationDecision(
        message_id="m_burst_4",
        stream_id="stream_cb",
        author_id="user_burst_4",
        author_name="UserBurst4",
        category=ModerationCategory.SPAM,
        confidence=0.95,
        recommended_action=ModerationAction.DELETE,
    )
    approved4, _, reason4 = policy.evaluate_action(dec4, config)
    assert approved4 is False
    assert config.circuit_breaker_tripped is True
    assert "Circuit Breaker TRIPPED" in reason4

    # 5th action must remain blocked while circuit breaker is tripped
    dec5 = ModerationDecision(
        message_id="m_burst_5",
        stream_id="stream_cb",
        author_id="user_burst_5",
        author_name="UserBurst5",
        category=ModerationCategory.SPAM,
        confidence=0.95,
        recommended_action=ModerationAction.DELETE,
    )
    approved5, _, reason5 = policy.evaluate_action(dec5, config)
    assert approved5 is False
    assert "Circuit Breaker is TRIPPED" in reason5

    # Explicit reset restores action capability
    policy.reset_circuit_breaker("stream_cb", config)
    assert config.circuit_breaker_tripped is False

    dec_after_reset = ModerationDecision(
        message_id="m_after_reset",
        stream_id="stream_cb",
        author_id="user_after",
        author_name="UserAfter",
        category=ModerationCategory.SPAM,
        confidence=0.95,
        recommended_action=ModerationAction.DELETE,
    )
    approved_after, _, _ = policy.evaluate_action(dec_after_reset, config)
    assert approved_after is True


def test_policy_circuit_breaker_multi_stream_isolation():
    """
    CRITICAL REQUIREMENT: Tripping circuit breaker in Stream A does NOT trip Stream B.
    """
    policy = ActionPolicy()
    config_a = StreamModerationConfig(
        circuit_breaker_action_threshold=3,
        cooldown_seconds_per_user=0,
    )
    config_b = StreamModerationConfig(
        circuit_breaker_action_threshold=3,
        cooldown_seconds_per_user=0,
    )

    # Trip Stream A
    for i in range(3):
        dec = ModerationDecision(
            message_id=f"a_{i}",
            stream_id="stream_A",
            author_id=f"u_{i}",
            author_name=f"U{i}",
            category=ModerationCategory.SPAM,
            recommended_action=ModerationAction.DELETE,
        )
        policy.evaluate_action(dec, config_a)

    assert config_a.circuit_breaker_tripped is True

    # Stream B must remain un-tripped and able to approve actions
    dec_b = ModerationDecision(
        message_id="b_1",
        stream_id="stream_B",
        author_id="u_b",
        author_name="UB",
        category=ModerationCategory.SPAM,
        recommended_action=ModerationAction.DELETE,
    )
    approved_b, _, _ = policy.evaluate_action(dec_b, config_b)
    assert approved_b is True
    assert config_b.circuit_breaker_tripped is False
