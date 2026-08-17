"""
Tests for Direct Mention Priority Elevation in GODDESS AI 2.0.
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


def test_direct_mention_elevates_priority_to_high():
    """Verify directly addressing the bot persona elevates decision priority to HIGH."""
    engine = EngagementDecisionEngine()
    config = CoHostConfig(enabled=True)
    config.personality.name = "Goddess"

    msg = CoHostMessage(
        stream_id="STREAM_A",
        message_id="msg_m1",
        author_id="user_1",
        author_name="Alice",
        message_text="Hey Goddess, what time does the stream end today?",
    )
    intent = CoHostIntent(intent_type=IntentType.MENTION, confidence=0.90)

    decision = engine.evaluate_engagement(msg, intent, config)

    assert decision.should_respond is True
    assert decision.priority == "HIGH"
    assert decision.response_type in (EngagementResponseType.ANSWER, EngagementResponseType.ACKNOWLEDGE)
