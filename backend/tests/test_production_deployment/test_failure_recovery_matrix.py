"""
Failure and Recovery Matrix Tests for GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.ai.decision_engine import AIDecisionEngine
from app.services.ai.models import AIActionType
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import CoHostResponse, ResponseStatus
from app.services.moderation.manager import ModerationManager
from app.services.youtube.models import ChatMessage


@pytest.fixture(autouse=True)
async def reset_safety():
    """Ensure clean safety controller state before and after each test."""
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_failure_matrix_gemini_outage_fails_closed():
    """Verify Gemini outage safely fails closed without crashing."""
    mock_mod = AsyncMock(spec=ModerationManager)
    mock_mod.process_message.return_value = None

    mock_co = AsyncMock(spec=CoHostManager)
    mock_co.handle_chat_message.return_value = CoHostResponse(
        stream_id="STREAM_MATRIX",
        message_id="msg_m_1",
        author_id="u_1",
        author_name="User",
        user_message="Hello",
        response_text="",
        status=ResponseStatus.FAILED,
        block_reason="Gemini offline",
    )

    engine = AIDecisionEngine(mod_mgr=mock_mod, co_mgr=mock_co)

    msg = ChatMessage(
        message_id="msg_m_1",
        stream_id="STREAM_MATRIX",
        author_id="u_1",
        author_name="User",
        message_text="Hello Goddess",
    )

    decision = await engine.evaluate_message(msg)
    assert decision.action == AIActionType.SAFE_PASS
    assert decision.should_reply is False
