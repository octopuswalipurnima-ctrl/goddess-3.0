"""
Tests for Gemini Quota Exhaustion & Multi-Key Failover in GODDESS AI 2.0.
"""

import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import CredentialUnavailableError


@pytest.mark.asyncio
async def test_gemini_429_quota_rotation_across_keys():
    """Verify 429 quota exhaustion rotates through configured keys."""
    keys = ["AIzaSyFakeKey111111111111111111111111", "AIzaSyFakeKey222222222222222222222222"]
    mgr = GeminiCredentialManager(keys=keys)

    # Key 1 initially active
    key_id_1, raw_1 = mgr.get_credential()
    assert key_id_1 == "gemini-key-1"

    # Trip quota on Key 1
    await mgr.mark_failed(key_id_1, error="ResourceExhausted: Quota exceeded", is_quota=True, status_code=429)

    # Key 2 should become active
    key_id_2, raw_2 = mgr.get_credential()
    assert key_id_2 == "gemini-key-2"

    # Trip quota on Key 2
    await mgr.mark_failed(key_id_2, error="ResourceExhausted: Quota exceeded", is_quota=True, status_code=429)

    # All keys exhausted -> CredentialUnavailableError
    with pytest.raises(CredentialUnavailableError):
        mgr.get_credential()
