"""
Asynchronous Token Bucket Rate Limiter for Google Gemini API.

Controls request frequency and prevents burst spikes from overwhelming API limits.
"""

import asyncio
import time
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.gemini.exceptions import RateLimitError

logger = get_logger("gemini.rate_limiter")


class TokenBucketRateLimiter:
    """Asynchronous Token Bucket rate limiter."""

    def __init__(
        self,
        capacity: Optional[float] = None,
        refill_rate: Optional[float] = None,
    ):
        self.capacity = capacity if capacity is not None else float(settings.gemini_rate_limit_capacity)
        self.refill_rate = refill_rate if refill_rate is not None else float(settings.gemini_rate_limit_refill_rate)
        self.tokens = self.capacity
        self.last_refill_timestamp = time.time()
        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill_timestamp
        if elapsed > 0:
            new_tokens = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill_timestamp = now

    async def acquire(self, tokens: float = 1.0, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket. Sleeps asynchronously if tokens are insufficient.
        Raises RequestTimeoutError or returns False if timeout expires.
        """
        start_time = time.time()

        while True:
            async with self._lock:
                now = time.time()
                self._refill(now)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                # Calculate required sleep duration
                needed = tokens - self.tokens
                wait_duration = needed / self.refill_rate

            # Check if waiting would exceed timeout
            if timeout is not None:
                elapsed_total = time.time() - start_time
                if elapsed_total + wait_duration > timeout:
                    raise RateLimitError(429, f"Rate limiter acquire timed out after {elapsed_total:.2f}s", "rateLimitExceeded")

            logger.debug(f"Rate limit reached. Waiting {wait_duration:.2f}s for refill...")
            try:
                await asyncio.sleep(min(wait_duration, 1.0))
            except asyncio.CancelledError:
                raise


# Global singleton instance of TokenBucketRateLimiter
gemini_rate_limiter = TokenBucketRateLimiter()
