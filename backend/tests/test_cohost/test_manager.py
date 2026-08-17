"""
Tests for CoHostManager End-to-End Processing, DRY_RUN Mode, and Event Dispatching.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_manager_dry_run_flow():
    """
    CRITICAL: Verify when dry_run=True, full pipeline runs, status is DRY_RUN,
    and YouTube posting is bypassed.
    """
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_dry",
        stream_id="stream_dry",
        status=AIResponseStatus.SUCCESS,
        text="Hey Alice, we are playing BGMI today!",
        model="gemini-2.5-flash",
    )
    generator = ResponseGenerator(ai_manager=mock_ai)
    manager = CoHostManager(generator=generator)

    # Enable Co-Host in DRY_RUN mode
    manager.update_config("stream_dry", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_dry_1",
        stream_id="stream_dry",
        author_id="user_alice",
        author_name="Alice",
        message_text="@goddess what game are we playing?",
    )

    response = await manager.process_message(msg)

    assert response is not None
    assert response.status == ResponseStatus.DRY_RUN
    assert "playing BGMI" in response.response_text
    assert manager.metrics.responses_dry_run >= 1
    assert manager.metrics.responses_sent == 0


@pytest.mark.asyncio
async def test_manager_disabled_opt_in_does_not_call_gemini():
    """Verify when Co-Host is disabled (default), Gemini is not called."""
    mock_ai = AsyncMock()
    generator = ResponseGenerator(ai_manager=mock_ai)
    manager = CoHostManager(generator=generator)

    # Co-Host is disabled by default
    cfg = manager.get_config("stream_default")
    assert cfg.enabled is False

    msg = ChatMessage(
        message_id="msg_disabled_1",
        stream_id="stream_default",
        author_id="user_bob",
        author_name="Bob",
        message_text="@goddess hi!",
    )

    response = await manager.process_message(msg)

    assert response is None
    assert mock_ai.request.call_count == 0
