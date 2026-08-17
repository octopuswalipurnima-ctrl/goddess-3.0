"""
Tests for Centralized AIDecisionEngine in GODDESS AI 2.0.
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


@pytest.mark.asyncio
async def test_ai_decision_engine_clean_message_evaluation():
    """Verify clean message triggers Co-Host decision path cleanly."""
    mock_mod = AsyncMock(spec=ModerationManager)
    mock_mod.process_message.return_value = None

    mock_co = AsyncMock(spec=CoHostManager)
    mock_co.handle_chat_message.return_value = CoHostResponse(
        stream_id="STREAM_DEC_1",
        message_id="msg_dec_1",
        author_id="user_1",
        author_name="GamerGuy",
        user_message="Hey Goddess what game is this?",
        response_text="Hey GamerGuy! We are streaming Minecraft today!",
        status=ResponseStatus.DRY_RUN,
        model="gemini-2.5-flash",
    )

    engine = AIDecisionEngine(mod_mgr=mock_mod, co_mgr=mock_co)
    engine.update_stream_config("STREAM_DEC_1", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_dec_1",
        stream_id="STREAM_DEC_1",
        author_id="user_1",
        author_name="GamerGuy",
        message_text="Hey Goddess what game is this?",
    )

    decision = await engine.evaluate_message(msg)
    assert decision.action == AIActionType.COHOST_DRY_RUN
    assert decision.should_reply is False  # Dry run
    assert decision.reply_text == "Hey GamerGuy! We are streaming Minecraft today!"
    assert decision.priority == "NORMAL"


@pytest.mark.asyncio
async def test_ai_decision_engine_emergency_stop_fail_closed():
    """Verify emergency stop triggers fail-closed decision immediately."""
    engine = AIDecisionEngine()
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_STOP", reason="Lockdown")

    msg = ChatMessage(
        message_id="msg_dec_stop",
        stream_id="STREAM_STOP",
        author_id="user_1",
        author_name="User",
        message_text="Hello Goddess",
    )

    decision = await engine.evaluate_message(msg)
    assert decision.action == AIActionType.FAIL_CLOSED
    assert decision.should_reply is False
    assert decision.should_moderate is False
    assert "Emergency Stop" in decision.reason

    await safety_controller.clear_emergency_stop(stream_id="STREAM_STOP")
