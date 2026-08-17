"""
End-to-End Co-Host Adaptive Intelligence Pipeline Tests for GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.manager import GeminiAIManager
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_end_to_end_adaptive_cohost_pipeline():
    """
    Verify complete flow:
    ChatMessage -> Context -> Intent -> Engagement Decision -> Awareness + Knowledge -> Gemini -> Policy -> Output
    """
    mock_ai = AsyncMock(spec=GeminiAIManager)
    mock_ai.request.return_value = AIResponse(
        request_id="req_e2e_cohost",
        stream_id="STREAM_E2E",
        status=AIResponseStatus.SUCCESS,
        model="gemini-2.5-flash",
        text="Our next stream is on Friday at 7 PM EST!",
    )

    gen = ResponseGenerator(ai_manager=mock_ai)
    mgr = CoHostManager(generator=gen)

    # Configure knowledge & stream awareness
    mgr.knowledge.set_fact("STREAM_E2E", "schedule", "Friday at 7 PM EST", category="schedule")
    mgr.awareness.set_activity("STREAM_E2E", "Valorant Tournament", category="Gaming")
    mgr.personality_mgr.update_personality("STREAM_E2E", {"name": "Goddess", "tone": "friendly"})

    mgr.update_config("STREAM_E2E", {"enabled": True, "dry_run": True, "respond_to_questions": True})

    msg = ChatMessage(
        message_id="msg_e2e_live_1",
        stream_id="STREAM_E2E",
        author_id="user_viewer_1",
        author_name="Charlie",
        message_text="When is your next stream scheduled?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)

    assert resp is not None
    assert resp.status == ResponseStatus.DRY_RUN
    assert "Friday at 7 PM EST" in resp.response_text
    assert resp.engagement_decision is not None
    assert resp.engagement_decision.should_respond is True
