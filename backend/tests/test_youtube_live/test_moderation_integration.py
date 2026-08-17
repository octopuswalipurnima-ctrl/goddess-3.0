"""
Tests for YouTube Live Chat & Moderation Pipeline Integration in GODDESS AI 2.0.
"""

import pytest
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ModerationAction
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_live_chat_message_enters_moderation_pipeline():
    """Verify incoming chat message is evaluated by Tier-1 regex rules and classified."""
    mod_mgr = ModerationManager()
    mod_mgr.update_config("STREAM_MOD_1", {"enabled": True, "dry_run": False})

    # Toxic message
    toxic_msg = ChatMessage(
        message_id="msg_mod_101",
        stream_id="STREAM_MOD_1",
        author_id="troll_1",
        author_name="Troll",
        message_text="YOU SUCK AND I HATE YOU IDIOT",
    )

    decision = await mod_mgr.process_message(toxic_msg)
    assert decision is not None
    assert decision.recommended_action != ModerationAction.NONE
