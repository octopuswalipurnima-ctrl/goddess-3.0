"""
Tests for Gemini Quota Fallback Model Usage in GODDESS AI 2.0.
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
async def test_gemini_quota_fallback_records_fallback_metadata():
    """Verify when Gemini fails over to fallback model, metadata is preserved."""
    mock_ai = AsyncMock(spec=GeminiAIManager)
    mock_ai.request.return_value = AIResponse(
        request_id="req_fallback",
        stream_id="STREAM_FALLBACK",
        status=AIResponseStatus.SUCCESS,
        model="gemini-2.5-flash-lite",
        text="Welcome to the broadcast!",
        metadata={"fallback_used": True},
    )

    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)
    mgr.update_config("STREAM_FALLBACK", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_fb_1",
        stream_id="STREAM_FALLBACK",
        author_id="user_1",
        author_name="Alice",
        message_text="Hello!",
    )

    resp = await mgr.process_message(msg)

    assert resp is not None
    assert resp.status == ResponseStatus.DRY_RUN
    assert resp.model == "gemini-2.5-flash-lite"
    assert resp.fallback_used is True
