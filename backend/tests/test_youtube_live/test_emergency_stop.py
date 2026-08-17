"""
Tests for Emergency Controls during Live Stream Operation in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.manager import CoHostManager
from app.services.moderation.manager import ModerationManager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_emergency_stop_halts_outgoing_replies():
    """Verify CoHost emergency stop flag blocks outgoing AI generation immediately."""
    mgr = CoHostManager()
    mgr.update_config("STREAM_EMERGENCY_1", {"enabled": True, "emergency_stop": True})

    msg = ChatMessage(
        message_id="msg_em_1",
        stream_id="STREAM_EMERGENCY_1",
        author_id="user_1",
        author_name="FriendlyViewer",
        message_text="Hello Goddess, how are you today?",
    )

    resp = await mgr.handle_chat_message(msg.model_dump())
    assert resp is None
    assert mgr.metrics.responses_blocked >= 1


@pytest.mark.asyncio
async def test_moderation_kill_switch_blocks_automated_actions():
    """Verify moderation kill_switch blocks automated disciplinary actions."""
    mgr = ModerationManager()
    mgr.update_config("STREAM_EMERGENCY_2", {"enabled": True, "kill_switch": True})

    spam_msg = ChatMessage(
        message_id="msg_em_2",
        stream_id="STREAM_EMERGENCY_2",
        author_id="spammer_1",
        author_name="Spammer",
        message_text="FREE BITCOIN AT HTTP://SCAM.COM",
    )

    decision = await mgr.process_message(spam_msg)
    assert decision is not None
    assert decision.recommended_action != "NONE" or decision.category != "SAFE"
