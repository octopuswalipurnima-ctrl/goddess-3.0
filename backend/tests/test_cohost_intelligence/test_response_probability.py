"""
Tests for Response Probability and Chatter Gating in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.engagement import EngagementDecisionEngine
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    EngagementResponseType,
    IntentType,
)


def test_response_probability_and_confidence_threshold_gating():
    """Verify messages below confidence threshold are silently passed."""
    engine = EngagementDecisionEngine()
    config = CoHostConfig(enabled=True, confidence_threshold=0.80)

    # Low confidence conversational topic
    msg = CoHostMessage(
        stream_id="STREAM_A",
        message_id="msg_low_conf",
        author_id="user_1",
        author_name="Bob",
        message_text="maybe that was okay",
    )
    intent = CoHostIntent(intent_type=IntentType.CONVERSATION, confidence=0.50)

    decision = engine.evaluate_engagement(msg, intent, config)

    assert decision.should_respond is False
    assert decision.response_type == EngagementResponseType.NO_RESPONSE
    assert "below threshold" in decision.reason
