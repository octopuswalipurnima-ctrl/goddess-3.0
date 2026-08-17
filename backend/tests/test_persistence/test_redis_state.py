"""
Tests for RedisStateManager transient state, cooldowns, idempotency, and TTL.
"""

import asyncio
import pytest
from app.core.redis import RedisStateManager


@pytest.mark.asyncio
async def test_redis_in_memory_cooldown_and_ttl():
    """Verify cooldowns and TTL expiration in RedisStateManager."""
    mgr = RedisStateManager(redis_url=None)  # Uses in-memory fallback

    # 1. Set Cooldown for 0.1s
    await mgr.set_cooldown("user_100", ttl_seconds=0.1)
    assert await mgr.is_on_cooldown("user_100") is True

    # 2. Wait for expiration
    await asyncio.sleep(0.12)
    assert await mgr.is_on_cooldown("user_100") is False


@pytest.mark.asyncio
async def test_redis_atomic_idempotency():
    """Verify atomic idempotency checking."""
    mgr = RedisStateManager(redis_url=None)

    # First check should succeed (lock acquired)
    first = await mgr.check_and_set_idempotency("stream_a:msg_1:DELETE", ttl_seconds=5.0)
    assert first is True

    # Second check must fail (duplicate detected)
    second = await mgr.check_and_set_idempotency("stream_a:msg_1:DELETE", ttl_seconds=5.0)
    assert second is False


@pytest.mark.asyncio
async def test_redis_rate_limit_counter():
    """Verify distributed rate limit counter increments."""
    mgr = RedisStateManager(redis_url=None)

    val1 = await mgr.increment_counter("stream_a:requests", ttl_seconds=60)
    assert val1 == 1

    val2 = await mgr.increment_counter("stream_a:requests", ttl_seconds=60)
    assert val2 == 2
