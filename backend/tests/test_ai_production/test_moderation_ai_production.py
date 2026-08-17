"""
Tests for 3-Tier Moderation Architecture & Tier-1 Outage Resilience in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.moderation.classifier import GeminiModerationClassifier
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ActionStatus, ModerationAction
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_tier1_regex_moderation_remains_active_during_gemini_outage():
    """Verify Tier 1 deterministic regex rules catch violations instantly even if Gemini classifier is down."""
    mock_ai = AsyncMock()
    mock_ai.request.side_effect = RuntimeError("Gemini 500 Outage")

    classifier = GeminiModerationClassifier(ai_manager=mock_ai)
    mgr = ModerationManager(classifier=classifier)
    mgr.update_config("STREAM_T1_MOD", {"enabled": True, "dry_run": True})

    # Obvious spam pattern caught by Tier 1 regex
    spam_msg = ChatMessage(
        message_id="msg_t1_1",
        stream_id="STREAM_T1_MOD",
        author_id="spammer_99",
        author_name="Spammer",
        message_text="FREE BITCOIN CLICK HERE HTTP://SCAM.CRYPTO.CC",
    )

    decision = await mgr.process_message(spam_msg)
    assert decision is not None
    assert decision.recommended_action != ModerationAction.NONE
    assert decision.source.value == "RULE_ENGINE"
