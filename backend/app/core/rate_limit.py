"""
Distributed & In-Memory Rate Limiting for GODDESS AI 2.0.

Provides rate limiting via Redis counters with automatic, fail-safe local fallback.
Protects login, emergency controls, and API endpoints against brute force and abuse.
"""

import time
from typing import Callable, Optional
from fastapi import Depends, Request

from app.auth.exceptions import RateLimitExceededException
from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_state

logger = get_logger("core.rate_limit")


class RateLimiter:
    """Rate limiter enforcing limits via Redis with safe local in-memory fallback."""

    def __init__(self, key_prefix: str, max_requests: int = 60, window_seconds: int = 60):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, identifier: str) -> None:
        """
        Check and increment rate limit counter for identifier (e.g. IP or username).
        Raises RateLimitExceededException if max_requests exceeded within window.
        """
        if not settings.rate_limit_enabled:
            return

        bucket_key = f"{self.key_prefix}:{identifier}"
        current_count = await redis_state.increment_counter(bucket_key, ttl_seconds=self.window_seconds)

        if current_count > self.max_requests:
            logger.warning(
                f"Rate limit exceeded for '{identifier}' on '{self.key_prefix}': "
                f"{current_count}/{self.max_requests} requests in {self.window_seconds}s"
            )
            raise RateLimitExceededException(
                detail=f"Rate limit exceeded ({self.max_requests} requests per {self.window_seconds}s). Please wait.",
                retry_after=self.window_seconds,
            )


def rate_limit(key_prefix: str, max_requests: int = 60, window_seconds: int = 60) -> Callable:
    """FastAPI Dependency factory for rate limiting by client IP."""
    limiter = RateLimiter(key_prefix=key_prefix, max_requests=max_requests, window_seconds=window_seconds)

    async def rate_limit_dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Combine IP and endpoint
        identifier = f"{client_ip}"
        await limiter.check(identifier)

    return rate_limit_dependency


# Preconfigured Standard Rate Limiters
auth_rate_limit = rate_limit("auth", max_requests=10, window_seconds=60)
emergency_rate_limit = rate_limit("emergency", max_requests=20, window_seconds=60)
api_rate_limit = rate_limit("api", max_requests=120, window_seconds=60)
