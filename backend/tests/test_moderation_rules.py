"""
Tests for Deterministic Rule Engine, Flood Detection, Repetition Analysis, Links, and Stream Isolation.
"""

import time
import pytest
from app.services.moderation.models import ModerationCategory, UserRole
from app.services.moderation.rules import RuleEngine
from app.services.youtube.models import ChatMessage


def test_rule_engine_clean_message():
    """Verify that a normal chat message returns None (no violation)."""
    engine = RuleEngine()
    msg = ChatMessage(
        message_id="m1",
        stream_id="stream_1",
        author_id="user_1",
        author_name="Alice",
        message_text="Hello streamer, loving the stream today!",
    )
    decision = engine.evaluate(msg)
    assert decision is None


def test_rule_engine_normal_url_is_not_malicious():
    """
    CRITICAL REQUIREMENT: Normal URLs (e.g. YouTube, Google, Twitch, GitHub)
    must NOT automatically be classified as malicious links.
    """
    engine = RuleEngine()
    normal_links = [
        "Check out this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "Search it on https://google.com",
        "Repo is at https://github.com/example/project",
        "My channel is https://twitch.tv/streamer",
    ]

    for idx, text in enumerate(normal_links):
        msg = ChatMessage(
            message_id=f"m_safe_link_{idx}",
            stream_id="stream_1",
            author_id="user_safe_link",
            author_name="FriendlyViewer",
            message_text=text,
        )
        decision = engine.evaluate(msg)
        assert decision is None, f"Expected normal URL '{text}' to NOT trigger malicious link detection"


def test_rule_engine_suspicious_link_detection():
    """Verify detection of suspicious links and phishing URLs with evidence-based confidence."""
    engine = RuleEngine()
    msg = ChatMessage(
        message_id="m2",
        stream_id="stream_1",
        author_id="user_spammer",
        author_name="BadActor",
        message_text="Click here for free gems: http://free-rewards-stream.xyz/claim",
    )
    decision = engine.evaluate(msg)
    assert decision is not None
    assert decision.category == ModerationCategory.MALICIOUS_LINK
    assert decision.confidence == 0.92
    assert decision.recommended_action.value == "DELETE"


def test_rule_engine_scam_keyword_detection():
    """Verify detection of cryptocurrency and financial scam patterns."""
    engine = RuleEngine()
    msg = ChatMessage(
        message_id="m3",
        stream_id="stream_1",
        author_id="user_scammer",
        author_name="CryptoBot",
        message_text="HUGE EVENT: send 0.5 btc and get 1.0 btc back immediately!",
    )
    decision = engine.evaluate(msg)
    assert decision is not None
    assert decision.category == ModerationCategory.SCAM
    assert decision.confidence == 0.92


def test_rule_engine_flood_burst_detection():
    """Verify detection of message flooding within a short time window and confidence calibration."""
    engine = RuleEngine()

    # User sends 4 messages rapidly
    for i in range(4):
        msg = ChatMessage(
            message_id=f"m_flood_{i}",
            stream_id="stream_1",
            author_id="flooder_1",
            author_name="Flooder",
            message_text=f"Message {i}",
        )
        assert engine.evaluate(msg) is None

    # 5th message triggers flood
    msg5 = ChatMessage(
        message_id="m_flood_5",
        stream_id="stream_1",
        author_id="flooder_1",
        author_name="Flooder",
        message_text="Message 5",
    )
    decision = engine.evaluate(msg5)
    assert decision is not None
    assert decision.category == ModerationCategory.FLOOD
    assert decision.confidence == 0.90
    assert decision.recommended_action.value == "SLOW_MODE"


def test_rule_engine_repeated_message_detection():
    """Verify detection of repeated identical messages and confidence scaling."""
    engine = RuleEngine()

    for i in range(2):
        msg = ChatMessage(
            message_id=f"m_rep_{i}",
            stream_id="stream_1",
            author_id="repeater_1",
            author_name="Repeater",
            message_text="Sub to my channel now!",
        )
        assert engine.evaluate(msg) is None

    # 3rd identical message triggers REPEATED_MESSAGE with calibrated confidence
    msg3 = ChatMessage(
        message_id="m_rep_3",
        stream_id="stream_1",
        author_id="repeater_1",
        author_name="Repeater",
        message_text="SUB TO MY CHANNEL NOW!!",
    )
    decision = engine.evaluate(msg3)
    assert decision is not None
    assert decision.category == ModerationCategory.REPEATED_MESSAGE
    assert decision.confidence == 0.85


def test_rule_engine_multi_stream_state_isolation():
    """
    CRITICAL: Verify that flood counters in Stream A do not impact Stream B.
    """
    engine = RuleEngine()

    # Flooder sends 4 messages in Stream A
    for i in range(4):
        msg_a = ChatMessage(
            message_id=f"a_{i}",
            stream_id="stream_A",
            author_id="user_same",
            author_name="Viewer",
            message_text=f"Msg {i}",
        )
        engine.evaluate(msg_a)

    # Now sends 1 message in Stream B -> MUST NOT trigger flood in Stream B!
    msg_b = ChatMessage(
        message_id="b_1",
        stream_id="stream_B",
        author_id="user_same",
        author_name="Viewer",
        message_text="Hello Stream B",
    )
    decision_b = engine.evaluate(msg_b)
    assert decision_b is None
