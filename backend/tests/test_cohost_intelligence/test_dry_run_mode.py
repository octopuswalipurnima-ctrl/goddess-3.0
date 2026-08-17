"""
Tests for Co-Host Dry Run Mode in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import CoHostConfig, ResponseStatus
from app.services.youtube.models import ChatMessage
from app.services.youtube.stream_manager import StreamManager


@pytest.mark.asyncio
async def test_dry_run_generates_reply_without_chat_writer_send():
    """Verify in DRY_RUN mode, response is marked DRY_RUN and LiveChatWriter is never called."""
    mock_yt_mgr = AsyncMock(spec=StreamManager)
    mgr = CoHostManager(yt_stream_mgr=mock_yt_mgr)

    # Configure Stream A with enabled=True, dry_run=True
    mgr.update_config("STREAM_DRY", {
        "enabled": True,
        "dry_run": True,
        "respond_to_questions": True,
    })

    msg = ChatMessage(
        message_id="msg_dry_1",
        stream_id="STREAM_DRY",
        author_id="user_1",
        author_name="Alice",
        message_text="What game is this?",
        is_question=True,
    )

    # Mock response generator
    mgr.generator.generate_response = AsyncMock()
    from app.services.cohost.models import CoHostIntent, CoHostResponse, IntentType
    mgr.generator.generate_response.return_value = CoHostResponse(
        stream_id="STREAM_DRY",
        message_id="msg_dry_1",
        author_id="user_1",
        author_name="Alice",
        response_text="We are playing Valorant!",
        status=ResponseStatus.APPROVED,
        intent=CoHostIntent(intent_type=IntentType.QUESTION),
    )

    resp = await mgr.process_message(msg)

    assert resp is not None
    assert resp.status == ResponseStatus.DRY_RUN
    assert resp.response_text == "We are playing Valorant!"
    mock_yt_mgr.get_session.assert_not_called()
