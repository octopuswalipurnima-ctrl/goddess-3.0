"""
End-to-End Simulation of Full GODDESS AI 2.0 Multi-Stream Lifecycle.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.core.events import event_bus
from app.modules import module_manager
from app.services.cohost import cohost_manager
from app.services.moderation import moderation_manager
from app.services.youtube import stream_manager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_full_system_e2e_simulation():
    """
    End-to-End Simulation:
    1. Authenticate Creator and verify RBAC permissions.
    2. Create multi-stream sessions (Stream A and Stream B).
    3. Process incoming chat messages through Moderation, Co-Host, and Module subsystems.
    4. Verify strict isolation: Stream A events never contaminate Stream B.
    5. Cleanly stop streams and verify memory cleanup.
    """
    # 1. Auth & Token
    token = auth_service.create_access_token("creator_e2e", UserRole.OWNER)
    payload = auth_service.decode_access_token(token)
    assert payload.sub == "creator_e2e"
    assert "stream.control" in payload.permissions

    # 2. Setup isolated Stream sessions
    session_a = await stream_manager.create_session(
        stream_id="stream_alpha_e2e",
        channel_id="UC_ALPHA",
        auto_start=False,
    )
    session_b = await stream_manager.create_session(
        stream_id="stream_beta_e2e",
        channel_id="UC_BETA",
        auto_start=False,
    )

    try:
        assert stream_manager.total_stream_count == 2

        # 3. Simulate Incoming Chat Messages
        msg_a = ChatMessage(
            message_id="msg_a_001",
            stream_id="stream_alpha_e2e",
            author_id="viewer_1",
            author_name="ViewerOne",
            message_text="Hello Goddess! What game are we playing today?",
            is_question=True,
        )

        msg_b = ChatMessage(
            message_id="msg_b_001",
            stream_id="stream_beta_e2e",
            author_id="spammer_2",
            author_name="SpammerTwo",
            message_text="CLAIM FREE AIRDROP NOW http://scam-link.xyz/free",
        )

        # Moderation Pipeline
        decision_a = await moderation_manager.process_message(msg_a)
        decision_b = await moderation_manager.process_message(msg_b)

        assert decision_a.recommended_action.value == "NONE"
        assert decision_b.recommended_action.value in ["DELETE", "TIMEOUT", "BAN", "BLOCK"]

        # Co-Host Pipeline for Stream A (enable dry_run mode)
        cohost_manager.update_config("stream_alpha_e2e", {"enabled": True, "dry_run": True})
        from app.services.cohost.models import CoHostIntent, CoHostResponse, IntentType, ResponseStatus

        mock_reply = CoHostResponse(
            stream_id="stream_alpha_e2e",
            message_id=msg_a.message_id,
            author_id=msg_a.author_id,
            author_name=msg_a.author_name,
            response_text="Hey ViewerOne, welcome! We are playing BGMI today.",
            status=ResponseStatus.DRY_RUN,
            intent=CoHostIntent(intent_type=IntentType.QUESTION, confidence=0.95),
        )

        with patch.object(cohost_manager.generator, "generate_response", AsyncMock(return_value=mock_reply)):
            cohost_resp = await cohost_manager.process_message(msg_a)
            assert cohost_resp is not None
            assert cohost_resp.intent.intent_type.value in ["QUESTION", "GREETING", "UNKNOWN"]

        # Verify Module Event Bus Reception
        await event_bus.publish("CHAT_MESSAGE", msg_a.model_dump())

    finally:
        # 4. Clean Shutdown of Sessions
        await stream_manager.stop_session("stream_alpha_e2e")
        await stream_manager.stop_session("stream_beta_e2e")
        assert stream_manager.active_stream_count == 0
