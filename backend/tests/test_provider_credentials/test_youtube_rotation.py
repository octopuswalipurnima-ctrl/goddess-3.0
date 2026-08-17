"""
Tests for YouTube Credential Manager Rotation & Failover in GODDESS AI 2.0.
"""

import pytest
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import CredentialUnavailableError
from app.services.youtube.models import CredentialState


def test_youtube_four_keys_round_robin():
    """Verify round-robin rotation across 4 configured YouTube API keys."""
    keys = ["YTKey11111111111111111111", "YTKey22222222222222222222", "YTKey33333333333333333333", "YTKey44444444444444444444"]
    mgr = YouTubeCredentialManager(keys=keys)

    assert mgr.configured_count == 4
    assert mgr.available_count == 4

    seen_keys = []
    for _ in range(4):
        key_id, raw_key = mgr.get_credential()
        seen_keys.append(raw_key)

    assert seen_keys == keys


@pytest.mark.asyncio
async def test_youtube_failure_and_rotation_sequence():
    """Verify single failure marks slot as COOLDOWN and rotates to next key."""
    keys = ["YTKey1", "YTKey2", "YTKey3"]
    mgr = YouTubeCredentialManager(keys=keys)

    k1_id, k1_raw = mgr.get_credential()
    assert k1_id == "youtube-key-1"
    assert k1_raw == "YTKey1"

    # Mark key 1 failed
    await mgr.mark_failed(k1_id, "Network timeout", status_code=504)

    # Next request must select key 2
    k2_id, k2_raw = mgr.get_credential()
    assert k2_id == "youtube-key-2"
    assert k2_raw == "YTKey2"

    # Mark key 2 successful
    await mgr.mark_success(k2_id)
    summary = mgr.get_health_summary()
    assert summary[1].consecutive_failures == 0
    assert summary[1].successful_requests == 1


@pytest.mark.asyncio
async def test_youtube_consecutive_failures_tracking():
    """Verify consecutive failures increment and reset upon success."""
    mgr = YouTubeCredentialManager(keys=["YTKeyA"])
    k_id, _ = mgr.get_credential()

    await mgr.mark_failed(k_id, "500 Server Error", status_code=500)
    summary = mgr.get_health_summary()
    assert summary[0].consecutive_failures == 1
    assert summary[0].failed_requests == 1

    await mgr.mark_success(k_id)
    summary_after = mgr.get_health_summary()
    assert summary_after[0].consecutive_failures == 0
    assert summary_after[0].successful_requests == 1
