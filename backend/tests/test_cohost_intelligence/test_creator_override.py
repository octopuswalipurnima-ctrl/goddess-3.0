"""
Tests for Creator Override Controls in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.manager import CoHostManager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_creator_override_instantly_disables_cohost():
    """Verify creator disabling Co-Host immediately blocks all future replies."""
    mgr = CoHostManager()
    mgr.update_config("STREAM_OVERRIDE", {"enabled": True, "dry_run": True})

    # Creator overrides and disables
    mgr.update_config("STREAM_OVERRIDE", {"enabled": False})

    msg = ChatMessage(
        message_id="msg_ov_1",
        stream_id="STREAM_OVERRIDE",
        author_id="user_1",
        author_name="Alice",
        message_text="Hello Goddess?",
        is_question=True,
    )

    resp = await mgr.process_message(msg)
    assert resp is None
