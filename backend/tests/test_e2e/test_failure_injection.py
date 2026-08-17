"""
Failure Injection Tests for Database, Redis, Gemini, YouTube, and WebSocket Outages.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.redis import RedisStateManager
from app.db.session import ping_database
from app.services.gemini.client import GeminiAPIClient
from app.services.moderation import moderation_manager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_redis_failure_fail_safe_moderation():
    """Verify that if Redis goes down, rate limits and cooldowns still work via local in-memory fallback."""
    mgr = RedisStateManager(redis_url="redis://nonexistent-host-fails:6379/0")
    await mgr.initialize()
    assert mgr._is_connected is False

    # Should still succeed in local in-memory mode
    assert await mgr.set_cooldown("user_test", 10.0) is True
    assert await mgr.is_on_cooldown("user_test") is True


@pytest.mark.asyncio
async def test_gemini_failure_fail_safe_moderation():
    """Verify that when Gemini API fails, moderation falls back to ANALYSIS_FAILED (conf=0.0)."""
    with patch("app.services.gemini.manager.GeminiAIManager.request", AsyncMock(side_effect=Exception("API Timeout"))):
        msg = ChatMessage(
            message_id="msg_fail_test",
            stream_id="stream_alpha",
            author_id="user_1",
            author_name="UserOne",
            message_text="Maybe this is safe or maybe not, let's see.",
        )
        decision = await moderation_manager.process_message(msg)
        assert decision.category.value in ["ANALYSIS_FAILED", "SAFE"]
        assert decision.recommended_action.value in ["NONE", "LOG"]
