"""
Tests for Complete AI Provider Outage Handling in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.ai.decision_engine import AIDecisionEngine
from app.services.ai.models import AIActionType
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import CoHostResponse, ResponseStatus
from app.services.moderation.manager import ModerationManager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_full_provider_outage_fails_closed_safely():
    """Verify complete Gemini outage results in SAFE_PASS with zero fabricated responses."""
    mock_mod = AsyncMock(spec=ModerationManager)
    mock_mod.process_message.return_value = None

    mock_co = AsyncMock(spec=CoHostManager)
    # Simulate Co-Host failing closed
    mock_co.handle_chat_message.return_value = CoHostResponse(
        stream_id="STREAM_OUTAGE",
        message_id="msg_outage",
        author_id="user_1",
        author_name="User",
        user_message="Hello",
        response_text="",
        status=ResponseStatus.FAILED,
        block_reason="Gemini provider offline",
    )

    engine = AIDecisionEngine(mod_mgr=mock_mod, co_mgr=mock_co)

    msg = ChatMessage(
        message_id="msg_outage",
        stream_id="STREAM_OUTAGE",
        author_id="user_1",
        author_name="User",
        message_text="Hello Goddess",
    )

    decision = await engine.evaluate_message(msg)
    assert decision.should_reply is False
    assert decision.action == AIActionType.SAFE_PASS
    assert "No Co-Host response" in decision.reason or "offline" in decision.reason
