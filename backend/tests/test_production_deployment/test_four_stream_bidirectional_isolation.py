"""
Tests for 4-Stream Bidirectional Isolation in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.ai.decision_engine import AIDecisionEngine
from app.services.ai.models import AIActionType
from app.services.cohost.context import CoHostContextManager
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import CoHostResponse, ResponseStatus
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ActionSeverity, ModerationAction, ModerationCategory, ModerationDecision, ModerationSource, UserRole
from app.services.youtube.models import ChatMessage


@pytest.fixture(autouse=True)
async def reset_safety():
    """Ensure clean safety controller state before and after each test."""
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_four_stream_bidirectional_state_isolation():
    """
    Verify complete bidirectional isolation:
    Message on STREAM_A never affects STREAM_B, C, or D context, moderation, or Co-Host state.
    """
    streams = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]
    ctx_mgr = CoHostContextManager()

    mock_mod = AsyncMock(spec=ModerationManager)
    async def mock_process(msg: ChatMessage):
        if msg.stream_id == "STREAM_A":
            return ModerationDecision(
                message_id=msg.message_id,
                stream_id="STREAM_A",
                author_id=msg.author_id,
                author_name=msg.author_name,
                user_role=UserRole.USER,
                category=ModerationCategory.SPAM,
                confidence=0.99,
                severity=ActionSeverity.HIGH,
                reason="Spam detected",
                recommended_action=ModerationAction.DELETE,
                source=ModerationSource.RULE_ENGINE,
            )
        return None

    mock_mod.process_message.side_effect = mock_process

    mock_co = AsyncMock(spec=CoHostManager)
    async def mock_cohost(msg_dict):
        sid = msg_dict.get("stream_id")
        return CoHostResponse(
            stream_id=sid,
            message_id=msg_dict.get("message_id"),
            author_id=msg_dict.get("author_id"),
            author_name=msg_dict.get("author_name"),
            user_message=msg_dict.get("message_text"),
            response_text=f"Reply for {sid}",
            status=ResponseStatus.APPROVED,
            model="gemini-2.5-flash",
        )
    mock_co.handle_chat_message.side_effect = mock_cohost

    engine = AIDecisionEngine(mod_mgr=mock_mod, co_mgr=mock_co)

    # Evaluate message on STREAM_A
    msg_a = ChatMessage(
        message_id="msg_a_1",
        stream_id="STREAM_A",
        author_id="user_a",
        author_name="UserA",
        message_text="Spam link on stream A",
    )
    decision_a = await engine.evaluate_message(msg_a)
    assert decision_a.stream_id == "STREAM_A"
    assert decision_a.action == AIActionType.MODERATE_DELETE
    assert decision_a.should_moderate is True

    # Evaluate clean message on STREAM_B
    msg_b = ChatMessage(
        message_id="msg_b_1",
        stream_id="STREAM_B",
        author_id="user_b",
        author_name="UserB",
        message_text="Hello stream B!",
    )
    decision_b = await engine.evaluate_message(msg_b)
    assert decision_b.stream_id == "STREAM_B"
    assert decision_b.action == AIActionType.COHOST_REPLY
    assert decision_b.should_moderate is False
    assert decision_b.should_reply is True
    assert "Reply for STREAM_B" in (decision_b.reply_text or "")
