"""
Tests for Safe Degradation when All Provider Credentials are Unavailable.
"""

import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import CredentialUnavailableError as GeminiCredentialUnavailableError
from app.services.moderation.models import ModerationAction
from app.services.moderation.rules import RuleEngine
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError as YTCredentialUnavailableError
from app.services.youtube.models import ChatMessage


def test_youtube_all_credentials_unavailable_raises():
    """Verify clean exception when YouTube has no available keys."""
    mgr = YouTubeCredentialManager(keys=[])
    assert mgr.available_count == 0
    with pytest.raises(YTCredentialUnavailableError):
        mgr.get_credential()


def test_gemini_all_credentials_unavailable_raises():
    """Verify clean exception when Gemini has no available keys."""
    mgr = GeminiCredentialManager(keys=[])
    assert mgr.available_count == 0
    with pytest.raises(GeminiCredentialUnavailableError):
        mgr.get_credential()


def test_moderation_rules_operate_when_gemini_unavailable():
    """Verify Tier-1 regex rules still block spam even when Gemini AI is totally unconfigured."""
    rules = RuleEngine()
    spam_msg = ChatMessage(
        stream_id="STREAM_DEGRADED",
        message_id="msg_001",
        channel_id="channel_degraded",
        author_id="user_spammer",
        author_name="Spammer",
        message_text="VISIT HTTPS://MALICIOUS-SCAM.XYZ FOR FREE CRYPTO",
    )
    decision = rules.evaluate(spam_msg)
    assert decision is not None
    assert decision.recommended_action in (ModerationAction.BLOCK, ModerationAction.WARN, ModerationAction.DELETE)
