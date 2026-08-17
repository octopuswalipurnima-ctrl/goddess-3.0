"""
Bounded Retry & Exponential Backoff Engine for GODDESS AI 2.0.

Provides configurable retry policies with exponential backoff, jitter,
maximum delay caps, and error-aware retryability rules.
"""

import asyncio
import random
from typing import Callable, Optional, TypeVar
from app.core.logging import get_logger
from app.core.provider_errors import ProviderErrorCode

logger = get_logger("core.retry")

T = TypeVar("T")


class RetryPolicy:
    """Configurable exponential backoff retry policy with jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.2,
        max_delay: float = 5.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max(0, max_retries)
        self.initial_delay = max(0.01, initial_delay)
        self.max_delay = max(self.initial_delay, max_delay)
        self.backoff_factor = max(1.0, backoff_factor)
        self.jitter = jitter

    def is_retryable(self, error_code: ProviderErrorCode) -> bool:
        """
        Determines whether a provider error warrants an immediate retry with backoff.
        Non-retryable errors (auth failures, invalid requests, quota exhaustion on same key)
        should immediately trigger credential rotation or fail closed.
        """
        if error_code in (
            ProviderErrorCode.RATE_LIMITED,
            ProviderErrorCode.TIMEOUT,
            ProviderErrorCode.NETWORK_ERROR,
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
        ):
            return True
        return False

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate backoff delay for the given attempt index (0-based or 1-based).
        Applies exponential backoff capped at max_delay, with optional +-20% jitter.
        """
        delay = self.initial_delay * (self.backoff_factor ** max(0, attempt))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add uniform jitter between 0.8x and 1.2x of calculated delay
            jitter_ratio = random.uniform(0.8, 1.2)
            delay = delay * jitter_ratio

        return round(delay, 4)

    async def sleep_for_attempt(self, attempt: int) -> float:
        """Calculates delay and sleeps asynchronously."""
        delay = self.calculate_delay(attempt)
        await asyncio.sleep(delay)
        return delay
