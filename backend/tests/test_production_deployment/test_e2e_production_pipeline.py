"""
End-to-End Production Pipeline Tests for GODDESS AI 2.0.
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
async def test_full_pipeline_event_bus_to_decision_execution():
    """Verify live chat message triggers EventBus, evaluation, safety gating, and decision generation."""
    mock_mod = AsyncMock(spec=ModerationManager)
    mock_mod.process_message.return_value = None

    mock_co = AsyncMock(spec=CoHostManager)
    mock_co.handle_chat_message.return_value = CoHostResponse(
        stream_id="STREAM_E2E",
        message_id="msg_e2e_1",
        author_id="user_e2e",
        author_name="Alice",
        user_message="Hello Goddess",
        response_text="Hello Alice! Welcome to the stream!",
        status=ResponseStatus.APPROVED,
        model="gemini-2.5-flash",
    )

    engine = AIDecisionEngine(mod_mgr=mock_mod, co_mgr=mock_co)

    msg = ChatMessage(
        message_id="msg_e2e_1",
        stream_id="STREAM_E2E",
        author_id="user_e2e",
        author_name="Alice",
        message_text="Hello Goddess",
    )

    decision = await engine.evaluate_message(msg)

    assert decision.action == AIActionType.COHOST_REPLY
    assert decision.should_reply is True
    assert decision.reply_text == "Hello Alice! Welcome to the stream!"
    assert decision.stream_id == "STREAM_E2E"
