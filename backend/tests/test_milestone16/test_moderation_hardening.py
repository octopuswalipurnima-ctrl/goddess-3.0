"""
Tests for Moderation Reliability & Fail-Closed Behavior in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
import pytest
from app.services.moderation.manager import moderation_manager
from app.services.youtube.models import ChatMessage


def test_moderation_tier1_deterministic_rules():
    """Verify tier 1 deterministic moderation rules flag blocked scam patterns instantly."""
    msg = ChatMessage(
        message_id="msg_mod_test_1",
        stream_id="STREAM_A",
        author_name="BadActor",
        author_id="bad_123",
        message_text="claim free airdrop now at fake site",
        published_at=datetime.now(timezone.utc).isoformat(),
    )

    decision = moderation_manager.rules.evaluate(msg)
    assert decision is not None
    assert decision.recommended_action.value in ["DELETE", "TIMEOUT", "WARN", "LOG"]
