"""
Tests for Gemini Credential Manager, 4-Key Rotation, Cooldown, and Recovery.
"""

import time
import pytest
from app.services.gemini.credentials import GeminiCredentialManager, GeminiCredentialSlot
from app.services.gemini.exceptions import CredentialUnavailableError
from app.services.gemini.models import CredentialState


def test_gemini_no_credentials():
    """Verify behavior when no Gemini API keys are configured."""
    mgr = GeminiCredentialManager(keys=[])
    assert mgr.configured_count == 0
    assert mgr.available_count == 0
    assert mgr.has_available_credentials is False

    with pytest.raises(CredentialUnavailableError):
        mgr.get_credential()


def test_gemini_single_credential():
    """Verify single credential retrieval."""
    mgr = GeminiCredentialManager(keys=["test_mock_gemini_key_1"])
    assert mgr.configured_count == 1
    assert mgr.available_count == 1

    key_id, raw = mgr.get_credential()
    assert key_id == "gemini-key-1"
    assert raw == "test_mock_gemini_key_1"


def test_gemini_four_keys_rotation():
    """Verify round-robin rotation across 4 credentials."""
    keys = ["GKey1", "GKey2", "GKey3", "GKey4"]
    mgr = GeminiCredentialManager(keys=keys)
    assert mgr.configured_count == 4
    assert mgr.available_count == 4

    seen = [mgr.get_credential()[1] for _ in range(4)]
    assert seen == ["GKey1", "GKey2", "GKey3", "GKey4"]


@pytest.mark.asyncio
async def test_gemini_credential_failure_and_cooldown():
    """Verify that failing key puts it in cooldown and rotates to next."""
    keys = ["GKeyA", "GKeyB"]
    mgr = GeminiCredentialManager(keys=keys)

    k1_id, _ = mgr.get_credential()
    assert k1_id == "gemini-key-1"

    # Mark key 1 failed with quota
    await mgr.mark_failed(k1_id, "Quota Exceeded", is_quota=True, cooldown_seconds=60)

    # Next call must yield key 2
    k2_id, raw2 = mgr.get_credential()
    assert k2_id == "gemini-key-2"
    assert raw2 == "GKeyB"

    # Health summary must never expose raw keys
    summary = mgr.get_health_summary()
    assert len(summary) == 4
    for slot in summary:
        assert slot.key_id.startswith("gemini-key-")
        assert not hasattr(slot, "raw_key")


def test_gemini_cooldown_expiry_recovery():
    """Verify that after cooldown timestamp passes, slot returns to AVAILABLE."""
    slot = GeminiCredentialSlot("gemini-key-1", "TestKey")
    now = time.time()
    slot.state = CredentialState.COOLDOWN
    slot.cooldown_until_timestamp = now - 5  # Expired

    assert slot.is_usable(now) is True
    assert slot.state == CredentialState.AVAILABLE
    assert slot.cooldown_until_timestamp is None
