"""
Tests for RuleIntentDetector, Mention Detection, Questions, and Calibrated Confidence.
"""

import pytest
from app.services.cohost.intents import RuleIntentDetector
from app.services.cohost.models import CoHostMessage, IntentType


def test_intent_detection_mentions():
    """Verify direct @goddess and bot mentions are detected."""
    detector = RuleIntentDetector()

    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m1",
        author_id="user_1",
        author_name="Alice",
        message_text="@goddess are you ready for the next match?",
    )
    intent = detector.detect_intent(msg)
    assert intent.intent_type == IntentType.QUESTION
    assert intent.confidence >= 0.85
    assert msg.is_mention is True


def test_intent_detection_greetings():
    """Verify greeting phrases trigger GREETING intent."""
    detector = RuleIntentDetector()

    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m2",
        author_id="user_2",
        author_name="Bob",
        message_text="Hello Goddess! Good evening everyone",
    )
    intent = detector.detect_intent(msg)
    assert intent.intent_type == IntentType.GREETING
    assert intent.confidence >= 0.85


def test_intent_detection_compliments():
    """Verify compliment phrases trigger COMPLIMENT intent."""
    detector = RuleIntentDetector()

    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m3",
        author_id="user_3",
        author_name="Charlie",
        message_text="You are the best bot ever goddess!",
    )
    intent = detector.detect_intent(msg)
    assert intent.intent_type == IntentType.COMPLIMENT
    assert intent.confidence >= 0.85


def test_intent_detection_command_requests_not_executed():
    """
    CRITICAL: Verify command prefix triggers COMMAND_REQUEST intent (for routing, not execution).
    """
    detector = RuleIntentDetector()

    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m4",
        author_id="user_4",
        author_name="Dave",
        message_text="!discord",
    )
    intent = detector.detect_intent(msg)
    assert intent.intent_type == IntentType.COMMAND_REQUEST
    assert intent.confidence == 0.95


def test_intent_detection_ignore_noise():
    """Verify very short messages or single emojis are categorized as IGNORE."""
    detector = RuleIntentDetector()

    msg = CoHostMessage(
        stream_id="stream_1",
        message_id="m5",
        author_id="user_5",
        author_name="Eve",
        message_text="gg",
    )
    intent = detector.detect_intent(msg)
    assert intent.intent_type == IntentType.IGNORE
    assert intent.confidence == 0.95
