"""
Tests for Gemini Credential Manager Rotation & Failover in GODDESS AI 2.0.
"""

import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import CredentialUnavailableError


def test_gemini_four_keys_round_robin():
    """Verify round-robin rotation across 4 configured Gemini API keys."""
    keys = ["GKey11111111111111111111", "GKey22222222222222222222", "GKey33333333333333333333", "GKey44444444444444444444"]
    mgr = GeminiCredentialManager(keys=keys)

    assert mgr.configured_count == 4
    assert mgr.available_count == 4

    seen_keys = []
    for _ in range(4):
        key_id, raw_key = mgr.get_credential()
        seen_keys.append(raw_key)

    assert seen_keys == keys


@pytest.mark.asyncio
async def test_gemini_failure_rotation_and_recovery():
    """Verify failing a credential rotates to next and success resets consecutive failures."""
    keys = ["GKeyA", "GKeyB", "GKeyC"]
    mgr = GeminiCredentialManager(keys=keys)

    k1_id, k1_raw = mgr.get_credential()
    assert k1_id == "gemini-key-1"
    assert k1_raw == "GKeyA"

    # Mark key 1 failed with 503 Overloaded
    await mgr.mark_failed(k1_id, "Model overloaded", status_code=503)

    # Next request must yield key 2
    k2_id, k2_raw = mgr.get_credential()
    assert k2_id == "gemini-key-2"
    assert k2_raw == "GKeyB"

    # Mark key 2 successful
    await mgr.mark_success(k2_id)
    summary = mgr.get_health_summary()
    assert summary[1].consecutive_failures == 0
    assert summary[1].successful_requests == 1
