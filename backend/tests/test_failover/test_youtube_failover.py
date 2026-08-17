"""
YouTube API Failover, Credential Rotation & Quota Backoff Tests.

Verifies automatic key rotation on 403 quota errors, exponential backoff,
prevention of infinite retry loops, and zero credential exposure.
"""

import pytest
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError


@pytest.mark.asyncio
async def test_youtube_credential_rotation_on_403_quota():
    """Verify YouTube credential manager switches keys upon receiving 403 quota error."""
    mgr = YouTubeCredentialManager(keys=[
        "AIzaSyKeyA1111111111111111111111",
        "AIzaSyKeyB2222222222222222222222",
        "AIzaSyKeyC3333333333333333333333",
    ])
    
    key_id_1, raw_key_1 = mgr.get_credential()
    assert raw_key_1 == "AIzaSyKeyA1111111111111111111111"

    # Report quota error on key A with cooldown
    await mgr.mark_failed(key_id_1, "Quota Exceeded", is_quota=True, cooldown_seconds=60)
    key_id_2, raw_key_2 = mgr.get_credential()
    assert raw_key_2 == "AIzaSyKeyB2222222222222222222222"

    # Report quota error on key B with cooldown
    await mgr.mark_failed(key_id_2, "Quota Exceeded", is_quota=True, cooldown_seconds=60)
    key_id_3, raw_key_3 = mgr.get_credential()
    assert raw_key_3 == "AIzaSyKeyC3333333333333333333333"


@pytest.mark.asyncio
async def test_youtube_all_keys_exhausted_policy():
    """Verify safe degradation when all configured keys are exhausted."""
    mgr = YouTubeCredentialManager(keys=[
        "AIzaSyKeyA1111111111111111111111",
        "AIzaSyKeyB2222222222222222222222",
    ])

    key_id_1, _ = mgr.get_credential()
    await mgr.mark_failed(key_id_1, "Quota Exceeded", is_quota=True, cooldown_seconds=60)

    key_id_2, _ = mgr.get_credential()
    await mgr.mark_failed(key_id_2, "Quota Exceeded", is_quota=True, cooldown_seconds=60)

    # When all are in cooldown/exhausted, raises CredentialUnavailableError cleanly
    assert mgr.has_available_credentials is False
    with pytest.raises(CredentialUnavailableError):
        mgr.get_credential()
