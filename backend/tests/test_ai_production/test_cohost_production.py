"""
Tests for Production AI Co-Host Behavior in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_fails_closed_without_fake_reply_when_gemini_fails():
    """Verify Co-Host returns NO_RESPONSE / None and does not invent fake replies on Gemini error."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_fail",
        stream_id="STREAM_CO_FAIL",
        status=AIResponseStatus.PROVIDER_ERROR,
        text="",
        error_message="503 Service Unavailable",
    )

    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)
    mgr.update_config("STREAM_CO_FAIL", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="m_co_fail",
        stream_id="STREAM_CO_FAIL",
        author_id="u_1",
        author_name="User",
        message_text="@goddess Can you give me advice?",
    )

    resp = await mgr.handle_chat_message(msg.model_dump())
    assert resp is not None
    assert resp.status == ResponseStatus.FAILED
    assert resp.response_text == ""
    assert "503" in (resp.block_reason or "")
