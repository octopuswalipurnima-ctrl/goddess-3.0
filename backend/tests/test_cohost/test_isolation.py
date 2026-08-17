"""
Tests for Multi-Stream Co-Host Isolation.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.response_generator import ResponseGenerator
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_multi_stream_config_and_cooldown_isolation():
    """
    CRITICAL: Verify enabling/replying on Stream A does NOT trigger or block Stream B.
    """
    mock_ai = AsyncMock()
    mock_ai.request.return_value = AIResponse(
        request_id="req_iso",
        stream_id="stream_A",
        status=AIResponseStatus.SUCCESS,
        text="Reply on Stream A",
        model="gemini-2.5-flash",
    )
    generator = ResponseGenerator(ai_manager=mock_ai)
    manager = CoHostManager(generator=generator)

    # Enable on Stream A only
    manager.update_config("stream_A", {"enabled": True, "dry_run": True, "personality": {"name": "Astra"}})
    cfg_b = manager.get_config("stream_B")
    assert cfg_b.enabled is False
    assert cfg_b.personality.name == "Goddess"

    # Message on Stream A produces response
    msg_a = ChatMessage(
        message_id="msg_a",
        stream_id="stream_A",
        author_id="user_1",
        author_name="Alice",
        message_text="@astra hello!",
    )
    res_a = await manager.process_message(msg_a)
    assert res_a is not None

    # Message on Stream B must NOT produce response (disabled)
    msg_b = ChatMessage(
        message_id="msg_b",
        stream_id="stream_B",
        author_id="user_1",
        author_name="Alice",
        message_text="@goddess hello!",
    )
    res_b = await manager.process_message(msg_b)
    assert res_b is None
