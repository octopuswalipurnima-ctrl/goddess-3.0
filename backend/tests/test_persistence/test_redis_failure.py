"""
Tests for Redis connection failure handling, safe local fallback, and health reporting.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.redis import RedisStateManager


@pytest.mark.asyncio
async def test_redis_failure_safe_fallback():
    """Verify that when Redis is unreachable, operations seamlessly fall back to local safe memory."""
    mgr = RedisStateManager(redis_url="redis://invalid-host-unreachable:6379/0")

    # Initializing will fail to connect, falling back to in-memory
    await mgr.initialize()
    assert mgr._is_connected is False

    # Should still safely prevent duplicate actions
    assert await mgr.check_and_set_idempotency("key123", ttl_seconds=10.0) is True
    assert await mgr.check_and_set_idempotency("key123", ttl_seconds=10.0) is False

    # Ping should report UNAVAILABLE with fallback mode
    ping = await mgr.ping()
    assert ping["status"] == "UNAVAILABLE"
    assert ping["mode"] == "FALLBACK_IN_MEMORY"
