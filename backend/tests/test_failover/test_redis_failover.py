"""
Redis Failover & In-Memory Fallback Resilience Tests.

Verifies continuous cooldown, rate limiting, and state tracking during Redis outages.
Enforces bounded in-memory store capacity (MAX_FALLBACK_KEYS = 10000).
"""

import asyncio
import pytest
from app.core.redis import InMemoryFallbackState, RedisStateManager, MAX_FALLBACK_KEYS


@pytest.mark.asyncio
async def test_redis_state_manager_offline_fallback():
    """Verify state manager gracefully operates in in-memory mode when Redis is unconfigured."""
    manager = RedisStateManager(redis_url=None)
    await manager.initialize()

    ping_result = await manager.ping()
    assert ping_result["mode"] == "IN_MEMORY"

    # Set and verify cooldown
    await manager.set_cooldown("user_stream_123", ttl_seconds=1.0)
    assert await manager.is_on_cooldown("user_stream_123") is True


@pytest.mark.asyncio
async def test_in_memory_fallback_ttl_expiration():
    """Verify fallback store purges expired keys automatically."""
    fallback = InMemoryFallbackState()
    await fallback.set("short_key", "value", ex=0.05)

    assert await fallback.get("short_key") == "value"
    await asyncio.sleep(0.06)
    assert await fallback.get("short_key") is None


@pytest.mark.asyncio
async def test_in_memory_fallback_bounded_capacity():
    """Verify fallback store does not grow beyond MAX_FALLBACK_KEYS."""
    fallback = InMemoryFallbackState()

    # Insert keys exceeding MAX_FALLBACK_KEYS
    for idx in range(MAX_FALLBACK_KEYS + 500):
        await fallback.set(f"key_{idx}", f"val_{idx}", ex=100.0)

    # Store must be bounded
    assert len(fallback._store) <= MAX_FALLBACK_KEYS
