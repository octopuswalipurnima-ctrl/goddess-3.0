"""Comprehensive tests for YouTube Data API key rotation, forensic error classification, diagnostics, and OAuth."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.youtube import (
    KeyState,
    LiveDetectionStatus,
    OAuthManager,
    YouTubeAPIUnavailableError,
    YouTubeClient,
    YouTubeKeyPool,
    YouTubeOAuthError,
)


@pytest.mark.asyncio
async def test_youtube_key_pool_initial_ready_state():
    """Verify that all configured keys begin in READY state."""
    keys = ["yt-key-1", "yt-key-2", "yt-key-3"]
    pool = YouTubeKeyPool(keys)

    assert pool.total_keys == 3
    assert pool.get_healthy_count() == 3
    summary = pool.get_status_summary()
    assert all(k["state"] == "READY" for k in summary)
    assert all(k["is_available"] is True for k in summary)


@pytest.mark.asyncio
async def test_youtube_key_pool_whitespace_and_empty_filtering():
    """Verify that whitespace or empty strings are not added to the key pool."""
    keys = ["yt-key-1", "", "   ", "yt-key-2"]
    pool = YouTubeKeyPool(keys)
    assert pool.total_keys == 2
    assert pool.get_healthy_count() == 2


@pytest.mark.asyncio
async def test_youtube_key_pool_rotation():
    """Test 3-key round robin and quota error backoff."""
    keys = ["yt-key-1", "yt-key-2", "yt-key-3"]
    pool = YouTubeKeyPool(keys)

    l1, k1 = await pool.get_next_key()
    assert l1 == "youtube-key-1"

    # Report quota error on key 1
    await pool.report_failure(
        label="youtube-key-1",
        status_code=403,
        reason="quotaExceeded",
        message="The request cannot be completed because you have exceeded your quota.",
        operation="search.list",
    )
    assert pool.get_healthy_count() == 2

    # Should rotate to key 2
    l2, k2 = await pool.get_next_key()
    assert l2 == "youtube-key-2"


@pytest.mark.asyncio
async def test_invalid_key_marks_invalid_without_poisoning_others():
    """Verify that a 400 keyInvalid marks only that key as INVALID and does not affect others."""
    keys = ["bad-key", "good-key-1", "good-key-2"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=400,
        reason="keyInvalid",
        message="API key not valid. Please pass a valid API key.",
        operation="channels.list",
    )

    summary = pool.get_status_summary()
    assert summary[0]["state"] == KeyState.INVALID.value
    assert summary[0]["is_available"] is False
    assert pool.get_healthy_count() == 2

    # Next key should be key 2
    label, _ = await pool.get_next_key()
    assert label == "youtube-key-2"


@pytest.mark.asyncio
async def test_api_not_enabled_marks_state():
    """Verify that 403 accessNotConfigured marks API_NOT_ENABLED."""
    keys = ["key-1", "key-2"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=403,
        reason="accessNotConfigured",
        message="YouTube Data API v3 has not been used in project 12345 before or it is disabled.",
        operation="search.list",
    )

    summary = pool.get_status_summary()
    assert summary[0]["state"] == KeyState.API_NOT_ENABLED.value
    assert summary[0]["is_available"] is False
    assert pool.get_healthy_count() == 1


@pytest.mark.asyncio
async def test_key_restrictions_forbidden_marks_state():
    """Verify that 403 ipRefererBlocked marks FORBIDDEN."""
    keys = ["key-1"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=403,
        reason="ipRefererBlocked",
        message="Requests from referer https://... are blocked.",
        operation="search.list",
    )

    summary = pool.get_status_summary()
    assert summary[0]["state"] == KeyState.FORBIDDEN.value
    assert summary[0]["is_available"] is False


@pytest.mark.asyncio
async def test_network_error_short_backoff():
    """Verify that network errors trigger transient 5s backoff rather than quota failure counts."""
    keys = ["key-1"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=0,
        reason="NetworkError",
        message="Connection timeout",
        operation="search.list",
    )

    summary = pool.get_status_summary()
    assert summary[0]["state"] == KeyState.NETWORK_ERROR.value
    assert summary[0]["failure_count"] == 0  # Does not increment quota failure counter


@pytest.mark.asyncio
async def test_cooldown_expiration_and_recovery():
    """Verify that an expired cooldown returns key state to READY."""
    keys = ["key-1"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=429,
        reason="rateLimitExceeded",
        message="Rate limit exceeded",
        operation="search.list",
    )

    assert pool.get_healthy_count() == 0
    # Manually set cooldown_until to past
    pool._keys[0].cooldown_until = datetime.now(UTC) - timedelta(seconds=1)

    assert pool.get_healthy_count() == 1
    label, _ = await pool.get_next_key()
    assert label == "youtube-key-1"


@pytest.mark.asyncio
async def test_youtube_key_pool_all_exhausted_detailed_diagnostics():
    """Test detailed exception message when all YouTube keys are exhausted."""
    keys = ["yt-key-1"]
    pool = YouTubeKeyPool(keys)

    await pool.report_failure(
        label="youtube-key-1",
        status_code=403,
        reason="quotaExceeded",
        message="Quota exceeded",
        operation="search.list",
    )
    with pytest.raises(YouTubeAPIUnavailableError) as exc_info:
        await pool.get_next_key()

    assert "youtube-key-1" in str(exc_info.value)
    assert "COOLDOWN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_diagnose_all_keys():
    """Test the diagnose_all_keys diagnostic function."""

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            key = request.url.params.get("key")
            if key == "valid_key":
                return httpx.Response(200, json={"items": [{"id": "UC123"}]}, request=request)
            elif key == "disabled_api_key":
                return httpx.Response(
                    403,
                    json={
                        "error": {
                            "code": 403,
                            "message": "API not enabled",
                            "errors": [{"reason": "accessNotConfigured"}],
                        }
                    },
                    request=request,
                )
            else:
                return httpx.Response(
                    400,
                    json={
                        "error": {
                            "code": 400,
                            "message": "Key invalid",
                            "errors": [{"reason": "keyInvalid"}],
                        }
                    },
                    request=request,
                )

    client = httpx.AsyncClient(transport=MockTransport())
    pool = YouTubeKeyPool(["valid_key", "disabled_api_key", "bad_key"])

    results = await pool.diagnose_all_keys(client=client)
    assert len(results) == 3
    assert results[0]["status"] == "READY"
    assert results[0]["http_code"] == 200

    assert results[1]["status"] == KeyState.API_NOT_ENABLED.value
    assert results[1]["http_code"] == 403

    assert results[2]["status"] == KeyState.INVALID.value
    assert results[2]["http_code"] == 400

    await client.aclose()


@pytest.mark.asyncio
async def test_youtube_client_live_detection_flow():
    """Test get_active_live_video and get_live_chat_id resolution."""

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/search" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {"videoId": "test_video_123"},
                                "snippet": {"title": "Live Gaming Stream"},
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "test_video_123",
                                "liveStreamingDetails": {
                                    "activeLiveChatId": "chat_id_abc_789",
                                },
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/channels" in url_str:
                return httpx.Response(
                    200,
                    json={"items": [{"id": "UC123", "snippet": {"title": "Test Channel"}}]},
                    request=request,
                )
            return httpx.Response(404, request=request)

    http_client = httpx.AsyncClient(transport=MockTransport())
    pool = YouTubeKeyPool(["valid_key_1"])
    yt = YouTubeClient(key_pool=pool, http_client=http_client)

    # 1. Channel lookup
    ch = await yt.get_channel_details("UC123")
    assert ch is not None
    assert ch["id"] == "UC123"

    # 2. Live video detection
    live_res = await yt.get_active_live_video("UC123")
    assert live_res.is_live is True
    assert live_res.video_id == "test_video_123"
    assert live_res.title == "Live Gaming Stream"

    # 3. Live chat ID resolution
    chat_id = await yt.get_live_chat_id("test_video_123")
    assert chat_id == "chat_id_abc_789"

    await yt.close()


@pytest.mark.asyncio
async def test_api_error_is_not_offline():
    """Verify that HTTP 400/500 API errors produce API_ERROR and are NOT marked OFFLINE."""

    class MockErrorTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "code": 400,
                        "message": "Bad Request",
                        "errors": [{"reason": "keyInvalid"}],
                    }
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockErrorTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)

    res = await yt.get_active_live_video("UCVQ8Qn1JPuZV8VzOgIdUGxQ")
    assert res.status != LiveDetectionStatus.OFFLINE
    assert res.is_offline is False
    assert res.is_error is True
    await yt.close()


@pytest.mark.asyncio
async def test_quota_error_is_not_offline():
    """Verify that 403 quotaExceeded produces QUOTA_ERROR and is NOT marked OFFLINE."""

    class MockQuotaTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockQuotaTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)

    res = await yt.get_active_live_video("UCVQ8Qn1JPuZV8VzOgIdUGxQ")
    assert res.status != LiveDetectionStatus.OFFLINE
    assert res.is_offline is False
    assert res.status == LiveDetectionStatus.QUOTA_ERROR
    await yt.close()


@pytest.mark.asyncio
async def test_network_error_is_not_offline():
    """Verify that connection failure produces NETWORK_ERROR and is NOT marked OFFLINE."""

    class MockNetworkFailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused to YouTube API")

    client = httpx.AsyncClient(transport=MockNetworkFailTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)

    res = await yt.get_active_live_video("UCVQ8Qn1JPuZV8VzOgIdUGxQ")
    assert res.status != LiveDetectionStatus.OFFLINE
    assert res.is_offline is False
    assert res.status == LiveDetectionStatus.NETWORK_ERROR
    await yt.close()


@pytest.mark.asyncio
async def test_successful_empty_result_is_offline():
    """Verify that only HTTP 200 with empty items produces OFFLINE."""

    class MockOfflineTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": []}, request=request)

    client = httpx.AsyncClient(transport=MockOfflineTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)

    res = await yt.get_active_live_video("UCVQ8Qn1JPuZV8VzOgIdUGxQ")
    assert res.status == LiveDetectionStatus.OFFLINE
    assert res.is_offline is True
    assert res.is_live is False
    assert res.is_error is False
    await yt.close()


@pytest.mark.asyncio
async def test_live_result_is_live():
    """Verify that HTTP 200 with active broadcast produces LIVE with extracted metadata."""

    class MockLiveTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": {"videoId": "vid_active_99"},
                            "snippet": {"title": "Active Live Stream"},
                        }
                    ]
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockLiveTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)

    res = await yt.get_active_live_video("UCVQ8Qn1JPuZV8VzOgIdUGxQ")
    assert res.status == LiveDetectionStatus.LIVE
    assert res.is_live is True
    assert res.video_id == "vid_active_99"
    assert res.title == "Active Live Stream"
    await yt.close()


@pytest.mark.asyncio
async def test_three_keys_are_attempted_when_available():
    """Verify that all 3 configured keys are attempted when key 1 and key 2 fail with retryable errors."""
    attempted_keys = []

    class MockMultiKeyTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            key = request.url.params.get("key")
            attempted_keys.append(key)
            if key == "key_3":
                return httpx.Response(200, json={"items": [{"id": "UC_OK"}]}, request=request)
            return httpx.Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockMultiKeyTransport())
    pool = YouTubeKeyPool(["key_1", "key_2", "key_3"])
    yt = YouTubeClient(key_pool=pool, http_client=client)

    data = await yt._execute_read_request("test.op", "https://api.test", {})
    assert data["items"][0]["id"] == "UC_OK"
    assert attempted_keys == ["key_1", "key_2", "key_3"]
    await yt.close()


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
