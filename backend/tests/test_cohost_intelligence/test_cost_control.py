"""
Tests for Cost Control and Gemini Call Suppression in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.manager import GeminiAIManager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cost_control_suppresses_gemini_calls_for_noise():
    """Verify low-value noise and command syntax never invoke Gemini."""
    mock_ai = AsyncMock(spec=GeminiAIManager)
    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)
    mgr.update_config("STREAM_COST", {"enabled": True, "dry_run": True})

    # Noise message
    noise_msg = ChatMessage(
        message_id="msg_noise_1",
        stream_id="STREAM_COST",
        author_id="user_1",
        author_name="Spammer",
        message_text="!points",
    )

    resp = await mgr.process_message(noise_msg)

    assert resp is None
    mock_ai.request.assert_not_called()
