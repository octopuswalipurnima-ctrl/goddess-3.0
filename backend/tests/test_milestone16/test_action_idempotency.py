"""
Tests for Action Idempotency Manager in GODDESS AI 2.0.
"""

import pytest
from app.core.idempotency import ActionIdempotencyManager


@pytest.mark.asyncio
async def test_action_idempotency_registration_and_duplication():
    """Verify duplicate actions are caught and blocked."""
    mgr = ActionIdempotencyManager(max_keys=100)

    # First execution -> succeeds
    first = await mgr.register_action("mod_ban_101", stream_id="STREAM_A", result_payload={"status": "BANNED"})
    assert first is True

    # Duplicate check -> True
    is_dup = await mgr.is_duplicate("mod_ban_101", stream_id="STREAM_A")
    assert is_dup is True

    # Second registration -> False
    second = await mgr.register_action("mod_ban_101", stream_id="STREAM_A")
    assert second is False

    # Retrieve cached payload
    cached = await mgr.get_cached_result("mod_ban_101", stream_id="STREAM_A")
    assert cached == {"status": "BANNED"}
