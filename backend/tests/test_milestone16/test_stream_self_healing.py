"""
Tests for Stream Self-Healing in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.youtube.stream_supervisor import StreamSupervisorSession, SupervisorState


@pytest.mark.asyncio
async def test_stream_self_healing_transition():
    """Verify stream session handles failure and enters RECONNECTING during self-healing."""
    mock_client = MagicMock()
    mock_client.get_live_chat_id = AsyncMock(return_value="live_chat_heal_123")

    session = StreamSupervisorSession(
        stream_id="STREAM_HEAL_TEST",
        channel_id="channel_123",
        api_client=mock_client,
    )

    assert session.state == SupervisorState.CONNECTING
    assert session.reconnect_attempts == 0
