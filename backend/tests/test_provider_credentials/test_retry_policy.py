"""
Tests for Bounded Retry Policy & Backoff in GODDESS AI 2.0.
"""

import pytest
from app.core.provider_errors import ProviderErrorCode
from app.core.retry import RetryPolicy


def test_retry_policy_delay_calculation():
    """Verify exponential backoff calculation within bounds."""
    policy = RetryPolicy(max_retries=3, initial_delay=0.1, max_delay=1.0, backoff_factor=2.0, jitter=False)

    assert policy.calculate_delay(0) == 0.1
    assert policy.calculate_delay(1) == 0.2
    assert policy.calculate_delay(2) == 0.4
    assert policy.calculate_delay(3) == 0.8
    assert policy.calculate_delay(4) == 1.0  # Capped at max_delay


def test_retry_policy_retryability_rules():
    """Verify transient errors are retryable and permanent errors are not."""
    policy = RetryPolicy()

    # Retryable transient errors
    assert policy.is_retryable(ProviderErrorCode.RATE_LIMITED) is True
    assert policy.is_retryable(ProviderErrorCode.TIMEOUT) is True
    assert policy.is_retryable(ProviderErrorCode.NETWORK_ERROR) is True
    assert policy.is_retryable(ProviderErrorCode.PROVIDER_UNAVAILABLE) is True

    # Non-retryable permanent errors (must rotate or fail closed)
    assert policy.is_retryable(ProviderErrorCode.AUTHENTICATION_FAILED) is False
    assert policy.is_retryable(ProviderErrorCode.PERMISSION_DENIED) is False
    assert policy.is_retryable(ProviderErrorCode.INVALID_REQUEST) is False
    assert policy.is_retryable(ProviderErrorCode.QUOTA_EXHAUSTED) is False


@pytest.mark.asyncio
async def test_retry_policy_sleep():
    """Verify async sleep execution for attempt."""
    policy = RetryPolicy(initial_delay=0.01, jitter=False)
    slept = await policy.sleep_for_attempt(0)
    assert slept == 0.01
