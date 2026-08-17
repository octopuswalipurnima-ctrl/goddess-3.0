"""
Tests for Fail-Closed Behavior on Gemini Failure (No Fake AI Responses) in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.manager import GeminiAIManager
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_gemini_outage_fails_closed_without_fake_reply():
    """Verify when Gemini fails, Co-Host returns FAILED status without synthetic fabricated reply."""
    mock_ai = AsyncMock(spec=GeminiAIManager)
    mock_ai.request.return_value = AIResponse(
        request_id="req_fail",
        stream_id="STREAM_FAIL",
        status=AIResponseStatus.MODEL_ERROR,
        error_message="503 Service Unavailable",
        text="",
    )

    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)
    mgr.update_config("STREAM_FAIL", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_fail_1",
        stream_id="STREAM_FAIL",
        author_id="user_1",
        author_name="Alice",
        message_text="What game is this?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)

    assert resp is not None
    assert resp.status == ResponseStatus.FAILED
    assert resp.response_text == ""
    assert "503 Service Unavailable" in (resp.block_reason or "")
