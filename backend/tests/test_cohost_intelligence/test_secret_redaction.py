"""
Tests for Zero Secret Redaction in Co-Host Outputs and Prompts in GODDESS AI 2.0.
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
async def test_unsafe_response_patterns_blocked_by_policy():
    """Verify responses containing accidental API keys or system instruction leaks are blocked."""
    mock_ai = AsyncMock(spec=GeminiAIManager)
    mock_ai.request.return_value = AIResponse(
        request_id="req_leak",
        stream_id="STREAM_LEAK",
        status=AIResponseStatus.SUCCESS,
        model="gemini-2.5-flash",
        text="Here is my API key: AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q",
    )

    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)
    mgr.update_config("STREAM_LEAK", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_lk_1",
        stream_id="STREAM_LEAK",
        author_id="user_1",
        author_name="Alice",
        message_text="What is your key?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)

    assert resp is not None
    assert resp.status == ResponseStatus.BLOCKED
    assert "forbidden system pattern" in (resp.block_reason or "")
