"""
Tests for YouTube Credential Manager, Rotation, Cooldown, and Recovery.
"""

import time
import pytest
from app.services.youtube.credentials import CredentialSlot, YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError
from app.services.youtube.models import CredentialState


def test_no_credentials_configured():
    """Verify state when no credentials are provided."""
    mgr = YouTubeCredentialManager(keys=[])
    assert mgr.configured_count == 0
    assert mgr.available_count == 0
    assert mgr.has_available_credentials is False

    with pytest.raises(CredentialUnavailableError):
        mgr.get_credential()


def test_single_credential_configured():
    """Verify single credential usage."""
    mgr = YouTubeCredentialManager(keys=["AIzaSyFakeKey123"])
    assert mgr.configured_count == 1
    assert mgr.available_count == 1
    assert mgr.has_available_credentials is True

    key_id, raw_key = mgr.get_credential()
    assert key_id == "youtube-key-1"
    assert raw_key == "AIzaSyFakeKey123"


def test_four_credentials_rotation():
    """Verify round-robin rotation across 4 credentials."""
    keys = ["KeyA", "KeyB", "KeyC", "KeyD"]
    mgr = YouTubeCredentialManager(keys=keys)
    assert mgr.configured_count == 4
    assert mgr.available_count == 4

    seen_keys = []
    for _ in range(4):
        key_id, raw_key = mgr.get_credential()
        seen_keys.append(raw_key)

    assert seen_keys == ["KeyA", "KeyB", "KeyC", "KeyD"]


@pytest.mark.asyncio
async def test_credential_failure_and_rotation():
    """Verify that failing a credential puts it into cooldown and selects the next key."""
    keys = ["Key1", "Key2"]
    mgr = YouTubeCredentialManager(keys=keys)

    # First key
    key_id, raw = mgr.get_credential()
    assert key_id == "youtube-key-1"

    # Mark key 1 failed with cooldown
    await mgr.mark_failed(key_id, "Quota Exceeded", is_quota=True, cooldown_seconds=10)

    # Next request must return key 2
    key_id2, raw2 = mgr.get_credential()
    assert key_id2 == "youtube-key-2"
    assert raw2 == "Key2"

    # Health summary must not expose raw secret
    summary = mgr.get_health_summary()
    assert len(summary) == 4
    for item in summary:
        assert item.key_id.startswith("youtube-key-")
        assert not hasattr(item, "raw_key")


def test_cooldown_automatic_recovery():
    """Verify that after cooldown duration expires, key returns to AVAILABLE."""
    slot = CredentialSlot("youtube-key-1", "TestKey")
    now = time.time()
    slot.state = CredentialState.COOLDOWN
    slot.cooldown_until_timestamp = now - 1  # Expired in past

    assert slot.is_usable(now) is True
    assert slot.state == CredentialState.AVAILABLE
    assert slot.cooldown_until_timestamp is None
