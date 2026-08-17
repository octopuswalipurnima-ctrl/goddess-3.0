"""
Tests for Asynchronous Token Bucket Rate Limiter.
"""

import asyncio
import time
import pytest
from app.services.gemini.exceptions import RateLimitError
from app.services.gemini.rate_limiter import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_immediate_acquire():
    """Verify immediate token acquisition within capacity."""
    limiter = TokenBucketRateLimiter(capacity=3.0, refill_rate=1.0)
    assert await limiter.acquire(tokens=1.0) is True
    assert await limiter.acquire(tokens=1.0) is True
    assert await limiter.acquire(tokens=1.0) is True
    assert limiter.tokens < 1.0


@pytest.mark.asyncio
async def test_rate_limiter_refill_over_time():
    """Verify tokens refill according to refill rate."""
    limiter = TokenBucketRateLimiter(capacity=2.0, refill_rate=10.0)  # 10 tokens / sec
    # Drain
    await limiter.acquire(tokens=2.0)
    assert limiter.tokens < 0.1

    # Sleep 0.15s -> should have at least 1.5 tokens
    await asyncio.sleep(0.15)
    acquired = await limiter.acquire(tokens=1.0)
    assert acquired is True


@pytest.mark.asyncio
async def test_rate_limiter_timeout_exceeded():
    """Verify that acquire raises RateLimitError when wait exceeds timeout."""
    limiter = TokenBucketRateLimiter(capacity=1.0, refill_rate=0.1)  # 10s per token
    await limiter.acquire(tokens=1.0)

    # Attempt to acquire with 0.05s timeout
    with pytest.raises(RateLimitError):
        await limiter.acquire(tokens=1.0, timeout=0.05)
