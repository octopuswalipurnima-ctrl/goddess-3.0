"""
Tests for ResponsePolicy Gate, Opt-In Disabled State, Emergency Stop, and Safety Filters.
"""

import pytest
from app.services.cohost.cooldowns import CoHostCooldownTracker
from app.services.cohost.deduplication import ResponseDeduplicator
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostResponse,
    IntentType,
    ResponseStatus,
)
from app.services.cohost.response_policy import ResponsePolicy


def test_response_policy_disabled_by_default():
    """Verify default disabled state blocks intent processing."""
    policy = ResponsePolicy()
    config = CoHostConfig(enabled=False)
    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m1",
        author_id="user_1",
        author_name="Alice",
        message_text="@goddess hi!",
        is_mention=True,
    )
    intent = CoHostIntent(intent_type=IntentType.GREETING, confidence=0.90)

    allowed, reason = policy.evaluate_intent(msg, intent, config)
    assert allowed is False
    assert "disabled" in reason.lower()


def test_response_policy_emergency_stop():
    """Verify emergency stop blocks intent processing."""
    policy = ResponsePolicy()
    config = CoHostConfig(enabled=True, emergency_stop=True)
    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m2",
        author_id="user_2",
        author_name="Bob",
        message_text="@goddess hi!",
        is_mention=True,
    )
    intent = CoHostIntent(intent_type=IntentType.GREETING, confidence=0.90)

    allowed, reason = policy.evaluate_intent(msg, intent, config)
    assert allowed is False
    assert "emergency stop" in reason.lower()


def test_response_policy_blocks_unsafe_patterns():
    """
    CRITICAL: Verify response containing simulated secret/key is blocked by safety filter.
    """
    policy = ResponsePolicy()
    config = CoHostConfig(enabled=True)
    response = CoHostResponse(
        stream_id="stream_1",
        message_id="m3",
        author_id="user_3",
        author_name="Charlie",
        response_text="My API key is AIzaSyD12345678901234567890123456789012 for your info",
        status=ResponseStatus.APPROVED,
    )

    approved, reason = policy.evaluate_response(response, config)
    assert approved is False
    assert "forbidden system pattern" in reason
