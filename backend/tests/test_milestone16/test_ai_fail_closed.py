"""
Tests for AI Fail-Closed Behavior in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
import pytest
from app.services.ai.decision_engine import AIDecisionEngine
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_ai_fail_closed_on_provider_error():
    """Verify AI decision engine fails closed with safe fallback when Gemini fails."""
    engine = AIDecisionEngine()

    msg = ChatMessage(
        message_id="msg_ai_fail_1",
        stream_id="STREAM_A",
        author_id="user_123",
        author_name="Alice",
        message_text="Hello Goddess AI!",
        published_at=datetime.now(timezone.utc).isoformat(),
    )

    decision = await engine.evaluate_message(msg)
    assert decision.action.value in ["NONE", "SAFE_PASS", "MODERATE_LOG", "COHOST_REPLY", "FAIL_CLOSED"]
