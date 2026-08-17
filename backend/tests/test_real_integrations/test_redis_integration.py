"""
Real Service Integration Audit: Redis Distributed State & Safe Fallback for GODDESS AI 2.0.
"""

import pytest
from app.core.redis import redis_state


@pytest.mark.asyncio
async def test_redis_state_manager_dedup_and_cooldowns():
    """Verify RedisStateManager handles cooldowns and message deduplication with safe fallbacks."""
    # Test idempotency key namespace
    is_first_seen1 = await redis_state.check_and_set_idempotency("msg_dedup_12345", ttl_seconds=60.0)
    assert is_first_seen1 is True

    # Second check must detect duplicate
    is_first_seen2 = await redis_state.check_and_set_idempotency("msg_dedup_12345", ttl_seconds=60.0)
    assert is_first_seen2 is False

    # Test cooldowns
    await redis_state.set_cooldown("test_action_cooldown", ttl_seconds=5.0)
    in_cd = await redis_state.is_on_cooldown("test_action_cooldown")
    assert in_cd is True
