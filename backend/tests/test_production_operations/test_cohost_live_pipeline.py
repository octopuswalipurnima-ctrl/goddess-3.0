"""
Tests for Production AI Co-Host Pipeline & Safety Gating in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_blocked_by_safety_controller_safe_mode():
    """Verify Co-Host reply generation is halted when stream enters Safe Mode."""
    mock_ai = AsyncMock()
    generator = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=generator)
    mgr.update_config("STREAM_CO_SAFE", {"enabled": True, "dry_run": True})

    # Enable safe mode
    await safety_controller.enable_safe_mode(stream_id="STREAM_CO_SAFE", reason="Stream volatility")

    msg = ChatMessage(
        message_id="msg_co_100",
        stream_id="STREAM_CO_SAFE",
        author_id="user_viewer",
        author_name="Viewer",
        message_text="@goddess What game are we playing?",
    )

    resp = await mgr.handle_chat_message(msg.model_dump())
    assert resp is None
    assert mgr.metrics.responses_blocked >= 1

    # Disable safe mode
    await safety_controller.disable_safe_mode(stream_id="STREAM_CO_SAFE")


@pytest.mark.asyncio
async def test_cohost_dry_run_generation_and_metrics():
    """Verify Co-Host in DRY_RUN mode generates reply but skips YouTube posting."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_dry_co",
        stream_id="STREAM_CO_DRY",
        status=AIResponseStatus.SUCCESS,
        text="Hey Viewer, we are playing BGMI!",
        model="gemini-2.5-flash",
    )
    generator = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=generator)
    mgr.update_config("STREAM_CO_DRY", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_co_101",
        stream_id="STREAM_CO_DRY",
        author_id="user_viewer",
        author_name="Viewer",
        message_text="@goddess What game are we playing?",
    )

    resp = await mgr.handle_chat_message(msg.model_dump())
    assert resp is not None
    assert resp.status == ResponseStatus.DRY_RUN
    assert mgr.metrics.responses_dry_run >= 1
