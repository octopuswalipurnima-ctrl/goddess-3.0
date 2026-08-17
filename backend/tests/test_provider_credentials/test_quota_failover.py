"""
Tests for Quota Exhaustion Detection & Failover in GODDESS AI 2.0.
"""

import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import CredentialUnavailableError
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError as YTCredentialUnavailableError


@pytest.mark.asyncio
async def test_youtube_quota_403_rotation():
    """Verify 403 quota error increments quota_failures and rotates immediately."""
    mgr = YouTubeCredentialManager(keys=["Key1", "Key2"])
    k1, _ = mgr.get_credential()

    await mgr.mark_failed(k1, "Quota exceeded daily limit", status_code=403)
    slot1 = mgr._slots[k1]
    assert slot1.quota_failures == 1

    # Immediate next key available
    k2, raw2 = mgr.get_credential()
    assert k2 == "youtube-key-2"
    assert raw2 == "Key2"


@pytest.mark.asyncio
async def test_gemini_quota_429_rotation():
    """Verify 429 quota error increments quota_failures and rotates immediately."""
    mgr = GeminiCredentialManager(keys=["GKey1", "GKey2"])
    k1, _ = mgr.get_credential()

    await mgr.mark_failed(k1, "Resource exhausted quota", status_code=429)
    slot1 = mgr._slots[k1]
    assert slot1.quota_failures == 1

    k2, raw2 = mgr.get_credential()
    assert k2 == "gemini-key-2"
    assert raw2 == "GKey2"


@pytest.mark.asyncio
async def test_all_youtube_quota_exhausted_fail_safe():
    """Verify CredentialUnavailableError is raised safely when all keys exhaust quota."""
    mgr = YouTubeCredentialManager(keys=["KeyA", "KeyB"])
    k1, _ = mgr.get_credential()
    await mgr.mark_failed(k1, "Quota error", is_quota=True)

    k2, _ = mgr.get_credential()
    await mgr.mark_failed(k2, "Quota error", is_quota=True)

    assert mgr.available_count == 0
    with pytest.raises(YTCredentialUnavailableError):
        mgr.get_credential()
