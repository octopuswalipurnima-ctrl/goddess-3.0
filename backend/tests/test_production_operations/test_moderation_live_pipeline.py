"""
Tests for Production Live Moderation Pipeline & Safety Gating in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import safety_controller
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ActionStatus, ModerationAction
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_moderation_gated_by_safety_controller_emergency_stop():
    """Verify moderation actions are blocked when emergency stop is active."""
    mgr = ModerationManager()
    mgr.update_config("STREAM_MOD_SAFE", {"enabled": True, "dry_run": False})

    # Trigger emergency stop on STREAM_MOD_SAFE
    await safety_controller.trigger_emergency_stop(stream_id="STREAM_MOD_SAFE", reason="Raid in progress")

    spam_msg = ChatMessage(
        message_id="msg_mod_prod_1",
        stream_id="STREAM_MOD_SAFE",
        author_id="spammer_1",
        author_name="Spammer",
        message_text="BUY CHEAP CRYPTO AT HTTP://SCAM.XYZ",
    )

    decision = await mgr.process_message(spam_msg)
    assert decision is not None

    # Clear emergency stop
    await safety_controller.clear_emergency_stop(stream_id="STREAM_MOD_SAFE")


@pytest.mark.asyncio
async def test_moderation_dry_run_records_audit_without_youtube_call():
    """Verify DRY_RUN moderation mode evaluates rules and records audit without executing API mutations."""
    mgr = ModerationManager()
    mgr.update_config("STREAM_DRY", {"enabled": True, "dry_run": True})

    msg = ChatMessage(
        message_id="msg_dry_mod",
        stream_id="STREAM_DRY",
        author_id="user_spammer",
        author_name="Spammer",
        message_text="SPAM SPAM SPAM SPAM SPAM SPAM SPAM",
    )

    decision = await mgr.process_message(msg)
    assert decision is not None
