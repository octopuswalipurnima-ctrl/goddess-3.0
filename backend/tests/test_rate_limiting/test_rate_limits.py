"""
Tests for Rate Limiting Enforcement and Fail-Safe Behavior.
"""

import pytest
from app.auth.exceptions import RateLimitExceededException
from app.core.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    """Verify rate limiter permits requests below the configured threshold."""
    limiter = RateLimiter(key_prefix="test_under", max_requests=5, window_seconds=10)

    # 5 requests should all succeed
    for _ in range(5):
        await limiter.check("user_allowed")


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Verify rate limiter raises RateLimitExceededException when exceeding threshold."""
    limiter = RateLimiter(key_prefix="test_over", max_requests=3, window_seconds=10)

    # 3 allowed
    for _ in range(3):
        await limiter.check("user_blocked")

    # 4th request must be blocked
    with pytest.raises(RateLimitExceededException) as exc_info:
        await limiter.check("user_blocked")

    assert exc_info.value.status_code == 429
