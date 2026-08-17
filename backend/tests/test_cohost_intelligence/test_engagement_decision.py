"""
Tests for Engagement Decision Engine in GODDESS AI 2.0.
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


def test_engagement_decision_answers_questions_and_ignores_spam():
    """Verify EngagementDecisionEngine approves relevant questions and ignores low-value noise."""
    engine = EngagementDecisionEngine()
    config = CoHostConfig(enabled=True)

    # 1. Clear question
    q_msg = CoHostMessage(
        stream_id="STREAM_A",
        message_id="msg_q1",
        author_id="user_1",
        author_name="Alice",
        message_text="What sensitivity do you play on?",
        is_question=True,
    )
    q_intent = CoHostIntent(intent_type=IntentType.QUESTION, confidence=0.95)
    dec_q = engine.evaluate_engagement(q_msg, q_intent, config)

    assert dec_q.should_respond is True
    assert dec_q.response_type == EngagementResponseType.ANSWER
    assert dec_q.confidence >= 0.88

    # 2. Repetitive noise
    spam_msg = CoHostMessage(
        stream_id="STREAM_A",
        message_id="msg_s1",
        author_id="user_2",
        author_name="Bob",
        message_text="aaaaaaaaaaaaaa",
    )
    spam_intent = CoHostIntent(intent_type=IntentType.IGNORE, confidence=0.99)
    dec_spam = engine.evaluate_engagement(spam_msg, spam_intent, config)

    assert dec_spam.should_respond is False
    assert dec_spam.response_type == EngagementResponseType.IGNORE
