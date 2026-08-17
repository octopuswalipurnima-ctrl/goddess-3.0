"""
Tests for GeminiModerationClassifier, Structured JSON Parsing, and Fail-Safe Behavior.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.moderation.classifier import GeminiModerationClassifier
from app.services.moderation.models import ModerationCategory, UserRole
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_classifier_valid_structured_json():
    """Verify parsing of valid JSON output from Gemini."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_1",
        stream_id="stream_1",
        status=AIResponseStatus.SUCCESS,
        text='{"category": "HARASSMENT", "confidence": 0.92, "severity": "HIGH", "reason": "Targeted insult against streamer", "recommended_action": "DELETE"}',
        model="gemini-2.5-flash",
    )

    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    msg = ChatMessage(
        message_id="msg_1",
        stream_id="stream_1",
        author_id="troll_1",
        author_name="TrollUser",
        message_text="You are terrible and nobody likes you",
    )

    decision = await classifier.classify(msg, role=UserRole.USER)

    assert decision.category == ModerationCategory.HARASSMENT
    assert decision.confidence == 0.92
    assert decision.severity.value == "HIGH"
    assert decision.recommended_action.value == "DELETE"
    assert decision.source.value == "GEMINI_AI"


@pytest.mark.asyncio
async def test_classifier_malformed_json_failsafe_is_analysis_failed():
    """
    CRITICAL REQUIREMENT: AI failure/malformed text must yield ANALYSIS_FAILED with confidence 0.0,
    NEVER category=SAFE.
    """
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_2",
        stream_id="stream_1",
        status=AIResponseStatus.SUCCESS,
        text="I think this message might be rude, but I am just answering in plain text.",
        model="gemini-2.5-flash",
    )

    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    msg = ChatMessage(
        message_id="msg_2",
        stream_id="stream_1",
        author_id="user_2",
        author_name="User2",
        message_text="Some ambiguous message",
    )

    decision = await classifier.classify(msg)

    # Must be ANALYSIS_FAILED with confidence 0.0, NOT SAFE!
    assert decision.category == ModerationCategory.ANALYSIS_FAILED
    assert decision.confidence == 0.0
    assert decision.recommended_action.value == "NONE"
    assert "Analysis Failed" in decision.reason


@pytest.mark.asyncio
async def test_classifier_ai_timeout_failsafe_is_analysis_failed():
    """
    CRITICAL REQUIREMENT: AI timeout must yield ANALYSIS_FAILED with confidence 0.0,
    NEVER category=SAFE.
    """
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_3",
        stream_id="stream_1",
        status=AIResponseStatus.TIMEOUT,
        text="",
        error_message="Request timed out after 10s",
    )

    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    msg = ChatMessage(
        message_id="msg_3",
        stream_id="stream_1",
        author_id="user_3",
        author_name="User3",
        message_text="Hello",
    )

    decision = await classifier.classify(msg)

    assert decision.category == ModerationCategory.ANALYSIS_FAILED
    assert decision.confidence == 0.0
    assert decision.recommended_action.value == "NONE"
