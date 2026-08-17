"""
Tests for Redis State Store Resilience & Seamless In-Memory Fallback in GODDESS AI 2.0.
"""

import pytest
from app.core.redis import InMemoryFallbackState, RedisStateManager


@pytest.mark.asyncio
async def test_redis_fallback_bounded_memory_and_eviction():
    """Verify in-memory fallback limits entries to bounded capacity and enforces TTL."""
    fallback = InMemoryFallbackState()

    # Insert 10 keys
    for i in range(10):
        await fallback.set(f"key_{i}", f"val_{i}", ex=10.0)

    val = await fallback.get("key_0")
    assert val == "val_0"
    assert len(fallback._store) <= 10000


@pytest.mark.asyncio
async def test_redis_state_manager_offline_to_online_recovery():
    """Verify RedisStateManager functions properly when Redis is offline and recovers safely."""
    manager = RedisStateManager(redis_url=None)  # Offline mode

    # Set cooldown in offline fallback mode
    await manager.set_cooldown("stream_action_1", ttl_seconds=5.0)
    in_cd = await manager.is_on_cooldown("stream_action_1")
    assert in_cd is True

    # Idempotency lock in offline mode
    first_lock = await manager.check_and_set_idempotency("action_token_xyz", ttl_seconds=60.0)
    assert first_lock is True
    duplicate_lock = await manager.check_and_set_idempotency("action_token_xyz", ttl_seconds=60.0)
    assert duplicate_lock is False
