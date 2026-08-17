"""
Tests for AI Co-Host Generation from YouTube Live Chat in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_dry_run_generates_response_without_live_post():
    """Verify Co-Host in DRY_RUN mode generates reply but skips posting to YouTube."""
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_dry_1",
        stream_id="STREAM_COHOST_1",
        status=AIResponseStatus.SUCCESS,
        text="Hey Bob, today we are playing Valorant!",
        model="gemini-2.5-flash",
    )
    generator = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=generator)
    mgr.update_config("STREAM_COHOST_1", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_cohost_101",
        stream_id="STREAM_COHOST_1",
        author_id="viewer_bob",
        author_name="Bob",
        message_text="@goddess What are we playing today?",
    )

    resp = await mgr.handle_chat_message(msg.model_dump())
    assert resp is not None
    assert resp.status == ResponseStatus.DRY_RUN
    assert "playing Valorant" in resp.response_text
    assert mgr.metrics.responses_dry_run >= 1
    assert mgr.metrics.responses_sent == 0
