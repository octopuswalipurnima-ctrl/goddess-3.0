"""
Tests for ModerationManager, End-to-End Processing, DRY_RUN Mode, and Multi-Stream Isolation.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.moderation.classifier import GeminiModerationClassifier
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ActionStatus, ModerationCategory
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_moderation_manager_clean_chat_flow():
    """Verify clean message produces SAFE decision without action."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_clean",
        stream_id="stream_1",
        status=AIResponseStatus.SUCCESS,
        text='{"category": "SAFE", "confidence": 0.98, "severity": "LOW", "reason": "Message is clean", "recommended_action": "NONE"}',
        model="gemini-2.5-flash",
    )
    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    manager = ModerationManager(classifier=classifier)

    msg = ChatMessage(
        message_id="msg_clean_1",
        stream_id="stream_1",
        author_id="viewer_1",
        author_name="GoodViewer",
        message_text="Great gameplay, keep it up!",
    )

    decision = await manager.process_message(msg)

    assert decision.category == ModerationCategory.SAFE
    assert decision.recommended_action.value == "NONE"
    assert manager.metrics.messages_analyzed >= 1


@pytest.mark.asyncio
async def test_moderation_manager_rule_match_flow():
    """Verify rule match (scam link) immediately triggers deletion action."""
    manager = ModerationManager()
    msg = ChatMessage(
        message_id="msg_scam_1",
        stream_id="stream_1",
        author_id="scammer_1",
        author_name="ScamBot",
        message_text="Free crypto rewards: http://claim-solana-rewards.xyz/bonus",
    )

    decision = await manager.process_message(msg)

    assert decision.category == ModerationCategory.MALICIOUS_LINK
    assert decision.recommended_action.value == "DELETE"
    assert manager.metrics.rule_matches >= 1
    assert manager.metrics.actions_executed >= 1


@pytest.mark.asyncio
async def test_moderation_manager_dry_run_mode():
    """
    CRITICAL REQUIREMENT: In DRY_RUN mode, action is evaluated & approved,
    audit record status is DRY_RUN, and real YouTube executor is bypassed.
    """
    manager = ModerationManager()
    manager.update_config("stream_dry", {"dry_run": True})

    msg = ChatMessage(
        message_id="msg_dry_1",
        stream_id="stream_dry",
        author_id="scammer_dry",
        author_name="ScamDry",
        message_text="Phishing link: http://steal-creds.xyz/login",
    )

    decision = await manager.process_message(msg)

    assert decision.category == ModerationCategory.MALICIOUS_LINK
    assert manager.metrics.actions_dry_run >= 1

    # Check audit log shows DRY_RUN
    records = manager.audit_logger.get_recent_records("stream_dry")
    assert len(records) >= 1
    assert records[-1].action_status == ActionStatus.DRY_RUN
    assert "DRY_RUN mode active" in records[-1].block_reason


@pytest.mark.asyncio
async def test_moderation_manager_ai_classification_flow():
    """Verify ambiguous message falls through to Gemini classifier."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_ai_1",
        stream_id="stream_1",
        status=AIResponseStatus.SUCCESS,
        text='{"category": "INSULT", "confidence": 0.88, "severity": "MEDIUM", "reason": "Severe derogatory insult", "recommended_action": "DELETE"}',
        model="gemini-2.5-flash",
    )
    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    manager = ModerationManager(classifier=classifier)

    msg = ChatMessage(
        message_id="msg_ai_insult",
        stream_id="stream_1",
        author_id="troll_2",
        author_name="TrollUser",
        message_text="You are an awful human being and should quit streaming",
    )

    decision = await manager.process_message(msg)

    assert decision.category == ModerationCategory.INSULT
    assert decision.confidence == 0.88
    assert decision.recommended_action.value == "DELETE"
    assert manager.metrics.ai_classifications >= 1


@pytest.mark.asyncio
async def test_moderation_manager_ai_failure_is_analysis_failed():
    """
    CRITICAL REQUIREMENT: If Gemini times out, result must be ANALYSIS_FAILED,
    and action must NOT execute on YouTube.
    """
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_fail",
        stream_id="stream_1",
        status=AIResponseStatus.TIMEOUT,
        text="",
        error_message="Gemini timed out",
    )
    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    manager = ModerationManager(classifier=classifier)

    msg = ChatMessage(
        message_id="msg_timeout",
        stream_id="stream_1",
        author_id="viewer_timeout",
        author_name="Viewer",
        message_text="Some message",
    )

    decision = await manager.process_message(msg)

    assert decision.category == ModerationCategory.ANALYSIS_FAILED
    assert decision.confidence == 0.0
    assert decision.recommended_action.value == "NONE"
    assert manager.metrics.ai_failures >= 1


@pytest.mark.asyncio
async def test_moderation_manager_stream_config_isolation():
    """Verify that pausing moderation on Stream A does not pause Stream B."""
    manager = ModerationManager()

    # Disable moderation on Stream A
    manager.update_config("stream_A", {"enabled": False})

    # Ensure Stream B remains enabled
    cfg_b = manager.get_config("stream_B")
    assert cfg_b.enabled is True

    # Message on Stream A -> No moderation action
    msg_a = ChatMessage(
        message_id="msg_a",
        stream_id="stream_A",
        author_id="bad_a",
        author_name="BadA",
        message_text="Scam link: http://scam.xyz/claim",
    )
    decision_a = await manager.process_message(msg_a)
    assert decision_a.category == ModerationCategory.MALICIOUS_LINK

    # Check audit log on Stream A was blocked due to config
    audit_a = manager.audit_logger.get_recent_records("stream_A")
    assert audit_a[-1].action_status.value == "BLOCKED"
    assert "Moderation is disabled" in audit_a[-1].block_reason
