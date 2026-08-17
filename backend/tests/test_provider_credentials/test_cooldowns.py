"""
Tests for Credential Cooldown & Automatic Recovery in GODDESS AI 2.0.
"""

import time
import pytest
from app.services.gemini.credentials import GeminiCredentialManager, GeminiCredentialSlot
from app.services.gemini.models import CredentialState
from app.services.youtube.credentials import CredentialSlot as YTCredentialSlot, YouTubeCredentialManager


def test_youtube_cooldown_automatic_recovery():
    """Verify that after cooldown expires, slot state returns to AVAILABLE."""
    slot = YTCredentialSlot("youtube-key-1", "TestKey")
    now = time.time()
    slot.state = CredentialState.COOLDOWN
    slot.cooldown_until_timestamp = now - 1.0  # Expired in past

    assert slot.is_usable(now) is True
    assert slot.state == CredentialState.AVAILABLE
    assert slot.cooldown_until_timestamp is None


def test_gemini_cooldown_automatic_recovery():
    """Verify that after cooldown expires, slot state returns to AVAILABLE."""
    slot = GeminiCredentialSlot("gemini-key-1", "TestGKey")
    now = time.time()
    slot.state = CredentialState.COOLDOWN
    slot.cooldown_until_timestamp = now - 1.0

    assert slot.is_usable(now) is True
    assert slot.state == CredentialState.AVAILABLE
    assert slot.cooldown_until_timestamp is None


@pytest.mark.asyncio
async def test_exponential_cooldown_growth():
    """Verify consecutive failures multiply cooldown duration up to max cap."""
    mgr = YouTubeCredentialManager(keys=["KeyA"])
    k_id, _ = mgr.get_credential()

    # 1st failure (base = 15s)
    await mgr.mark_failed(k_id, "Error 1", cooldown_seconds=15)
    slot = mgr._slots[k_id]
    t1 = slot.cooldown_until_timestamp

    # 2nd consecutive failure (multiplier = 2x)
    await mgr.mark_failed(k_id, "Error 2", cooldown_seconds=15)
    t2 = slot.cooldown_until_timestamp
    assert slot.consecutive_failures == 2
    assert t2 > t1
