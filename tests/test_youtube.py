"""Tests for YouTube Data API key rotation, OAuth manager, and API calls."""

import asyncio

import httpx
import pytest

from app.youtube import (
    OAuthManager,
    YouTubeAPIUnavailableError,
    YouTubeKeyPool,
    YouTubeOAuthError,
)


@pytest.mark.asyncio
async def test_youtube_key_pool_rotation():
    """Test 3-key round robin and quota error backoff."""
    keys = ["yt-key-1", "yt-key-2", "yt-key-3"]
    pool = YouTubeKeyPool(keys)

    assert pool.total_keys == 3
    assert pool.get_healthy_count() == 3

    l1, k1 = await pool.get_next_key()
    assert l1 == "youtube-key-1"

    # Report quota error on key 1
    await pool.report_failure("youtube-key-1", 403, "quotaExceeded")
    assert pool.get_healthy_count() == 2

    # Should rotate to key 2
    l2, k2 = await pool.get_next_key()
    assert l2 == "youtube-key-2"


@pytest.mark.asyncio
async def test_youtube_key_pool_all_exhausted():
    """Test exception when all YouTube keys are exhausted."""
    keys = ["yt-key-1"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure("youtube-key-1", 429, "rateLimitExceeded")
    with pytest.raises(YouTubeAPIUnavailableError):
        await pool.get_next_key()


@pytest.mark.asyncio
async def test_oauth_manager_refresh_locking():
    """Test that concurrent token refresh attempts are locked and do not cause stampedes."""
    refresh_call_count = 0

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            nonlocal refresh_call_count
            refresh_call_count += 1
            await asyncio.sleep(0.05)  # Simulate network latency
            return httpx.Response(
                200,
                json={
                    "access_token": f"new_token_{refresh_call_count}",
                    "expires_in": 3600,
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockTransport())
    oauth_mgr = OAuthManager(
        client_id="test_client_id",
        client_secret="test_client_secret",
        access_token=None,
        refresh_token="test_refresh_token",
    )

    # Launch 5 concurrent refresh calls
    tasks = [oauth_mgr.get_valid_token(client) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All should get the same valid token
    assert all(r == "new_token_1" for r in results)
    # Only 1 actual network refresh call occurred
    assert refresh_call_count == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_oauth_manager_invalid_grant():
    """Test that invalid_grant marks reauth required and stops infinite retries."""

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                text='{"error": "invalid_grant", "error_description": "Bad Request"}',
                request=request,
            )

    client = httpx.AsyncClient(transport=MockTransport())
    oauth_mgr = OAuthManager(
        client_id="test_client_id",
        client_secret="test_client_secret",
        access_token=None,
        refresh_token="revoked_token",
    )

    with pytest.raises(YouTubeOAuthError):
        await oauth_mgr.get_valid_token(client)

    assert oauth_mgr.is_reauth_required is True

    # Subsequent call immediately fails with reauth required
    with pytest.raises(YouTubeOAuthError, match="OAUTH_REAUTH_REQUIRED"):
        await oauth_mgr.get_valid_token(client)

    await client.aclose()
