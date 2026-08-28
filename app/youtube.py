"""YouTube Data API v3 Client with 3-key pool rotation, forensic diagnostics, and OAuth2 manager."""

import asyncio
import contextlib
import random
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import httpx

from app.config import settings
from app.utils import get_logger

logger = get_logger("goddess.youtube")


class KeyState(StrEnum):
    """Lifecycle and health states for YouTube Data API keys."""

    READY = "READY"
    COOLDOWN = "COOLDOWN"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    INVALID = "INVALID"
    API_NOT_ENABLED = "API_NOT_ENABLED"
    FORBIDDEN = "FORBIDDEN"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class YouTubeAPIUnavailableError(Exception):
    """Raised when all YouTube API keys in the pool are exhausted, in cooldown, or invalid."""


class YouTubeOAuthError(Exception):
    """Raised when OAuth authentication or refresh fails."""


class YouTubeKeyItem:
    """Tracks individual state, metrics, and cooldown for a single YouTube Data API key."""

    def __init__(self, label: str, key: str) -> None:
        self.label = label
        self.key = key.strip()
        self.state: KeyState = KeyState.READY
        self.cooldown_until: datetime | None = None
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_status_code: int | None = None
        self.last_reason: str | None = None
        self.last_error_message: str | None = None
        self.last_operation: str | None = None
        self.last_used: datetime | None = None
        self.created_at: datetime = datetime.now(UTC)

    def is_available(self) -> bool:
        """Check if key is ready for requests."""
        # Permanent configuration failures for this specific key
        if self.state in (KeyState.INVALID, KeyState.API_NOT_ENABLED, KeyState.FORBIDDEN):
            return False

        # If key is in cooldown, check if cooldown duration has expired
        if self.cooldown_until is not None:
            now = datetime.now(UTC)
            if now < self.cooldown_until:
                return False
            # Cooldown expired: restore key to READY state
            self.state = KeyState.READY
            self.cooldown_until = None
            logger.info(f"YouTube key [{self.label}] cooldown expired; state returned to READY.")

        return self.state == KeyState.READY

    def mark_success(self, operation: str = "") -> None:
        """Update metrics on successful call."""
        self.state = KeyState.READY
        self.success_count += 1
        self.failure_count = 0
        self.cooldown_until = None
        self.last_used = datetime.now(UTC)
        self.last_operation = operation
        self.last_error_message = None
        self.last_reason = None
        self.last_status_code = 200

    def mark_failure(
        self,
        status_code: int,
        reason: str,
        message: str,
        domain: str = "",
        operation: str = "",
    ) -> None:
        """Classify error and update key state accordingly."""
        self.last_status_code = status_code
        self.last_reason = reason
        self.last_error_message = message
        self.last_operation = operation
        self.last_used = datetime.now(UTC)

        reason_lower = (reason or "").lower()
        msg_lower = (message or "").lower()

        # 1. Invalid Key (HTTP 400 keyInvalid / badRequest)
        if status_code == 400 and ("keyinvalid" in reason_lower or "api key not valid" in msg_lower):
            self.state = KeyState.INVALID
            logger.error(
                f"YouTube API key [{self.label}] is INVALID (HTTP 400 {reason}).\n"
                f"  Operation: {operation}\n"
                f"  Message: {message}\n"
                f"  Action: Check YOUTUBE_API_KEY environment variable and verify the key string."
            )
            return

        # 2. API Not Enabled (HTTP 403 accessNotConfigured / SERVICE_DISABLED)
        if status_code == 403 and (
            "accessnotconfigured" in reason_lower
            or "service_disabled" in reason_lower
            or "has not been used in project" in msg_lower
            or "is disabled" in msg_lower
        ):
            self.state = KeyState.API_NOT_ENABLED
            logger.error(
                f"YouTube API key [{self.label}] failed: 'YouTube Data API v3' is NOT ENABLED in Google Cloud.\n"
                f"  Operation: {operation}\n"
                f"  Status: HTTP 403 ({reason})\n"
                f"  Message: {message}\n"
                f"  Action: Open Google Cloud Console -> APIs & Services -> Library -> Search 'YouTube Data API v3' -> Click ENABLE."
            )
            return

        # 3. Key Restrictions Blocked (HTTP 403 ipRefererBlocked / forbidden)
        if status_code == 403 and (
            "iprefererblocked" in reason_lower
            or "http_referrer_blocked" in reason_lower
            or "ip_address_blocked" in reason_lower
            or "blocked" in msg_lower
        ):
            self.state = KeyState.FORBIDDEN
            logger.error(
                f"YouTube API key [{self.label}] restriction blocked (HTTP 403 {reason}).\n"
                f"  Operation: {operation}\n"
                f"  Message: {message}\n"
                f"  Action: In Google Cloud Console -> Credentials -> Edit API Key -> Application restrictions: set to 'None' for server-side bot use."
            )
            return

        # 4. Genuine Quota Exceeded / Rate Limit (HTTP 403 quotaExceeded / 429)
        if status_code in (403, 429) and (
            "quotaexceeded" in reason_lower
            or "dailylimitexceeded" in reason_lower
            or "ratelimitexceeded" in reason_lower
            or "userratelimitexceeded" in reason_lower
            or "resource_exhausted" in reason_lower
            or status_code == 429
        ):
            self.failure_count += 1
            self.state = KeyState.COOLDOWN
            # Base cooldown: 30s * 2^(failures - 1), max 900s, with jitter
            base_sec = min(30 * (2 ** (self.failure_count - 1)), 900)
            jitter = random.uniform(0.9, 1.1)
            duration_sec = base_sec * jitter
            self.cooldown_until = datetime.now(UTC) + timedelta(seconds=duration_sec)
            logger.warning(
                f"YouTube API key [{self.label}] placed in COOLDOWN ({duration_sec:.1f}s).\n"
                f"  Operation: {operation}\n"
                f"  Status: HTTP {status_code} ({reason})\n"
                f"  Message: {message}\n"
                f"  Failures in sequence: {self.failure_count}"
            )
            return

        # 5. Network / Timeout Error (status_code == 0)
        if status_code == 0:
            self.state = KeyState.NETWORK_ERROR
            # Short 5-second backoff; do not increment quota failure count
            self.cooldown_until = datetime.now(UTC) + timedelta(seconds=5.0)
            logger.warning(
                f"YouTube API key [{self.label}] transient network error on {operation}: {message} (backoff 5.0s)"
            )
            return

        # 6. Other / Unknown HTTP Error (500, 502, 503, etc.)
        self.state = KeyState.UNKNOWN_ERROR
        self.cooldown_until = datetime.now(UTC) + timedelta(seconds=15.0)
        logger.warning(
            f"YouTube API key [{self.label}] HTTP {status_code} error on {operation}: {message} (backoff 15.0s)"
        )


class YouTubeKeyPool:
    """Thread-safe round-robin pool for YouTube Data API keys with failure isolation."""

    def __init__(self, keys: list[str]) -> None:
        clean_keys = [k.strip() for k in keys if k and k.strip()]
        self._keys: list[YouTubeKeyItem] = [
            YouTubeKeyItem(f"youtube-key-{i + 1}", key) for i, key in enumerate(clean_keys)
        ]
        self._index: int = 0
        self._lock = asyncio.Lock()

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    def get_healthy_count(self) -> int:
        return sum(1 for k in self._keys if k.is_available())

    def get_status_summary(self) -> list[dict[str, Any]]:
        """Return safe, credential-free status dictionary for each key."""
        now = datetime.now(UTC)
        summary = []
        for k in self._keys:
            cooldown_left = 0.0
            if k.cooldown_until and k.cooldown_until > now:
                cooldown_left = round((k.cooldown_until - now).total_seconds(), 1)

            summary.append(
                {
                    "label": k.label,
                    "state": k.state.value,
                    "is_available": k.is_available(),
                    "success_count": k.success_count,
                    "failure_count": k.failure_count,
                    "cooldown_remaining_sec": cooldown_left,
                    "last_status_code": k.last_status_code,
                    "last_reason": k.last_reason,
                    "last_operation": k.last_operation,
                }
            )
        return summary

    async def get_next_key(self) -> tuple[str, str]:
        """Select next available healthy key via round-robin."""
        async with self._lock:
            if not self._keys:
                raise YouTubeAPIUnavailableError("No YouTube API keys configured in environment.")

            # Search starting from current index
            for _ in range(len(self._keys)):
                key_item = self._keys[self._index]
                self._index = (self._index + 1) % len(self._keys)
                if key_item.is_available():
                    return key_item.label, key_item.key

            # All keys are currently unavailable; compile forensic diagnostic report
            diagnostics = []
            for k in self._keys:
                detail = f"[{k.label}]: State={k.state.value}"
                if k.last_status_code:
                    detail += f" (HTTP {k.last_status_code} {k.last_reason or ''})"
                if k.cooldown_until and k.cooldown_until > datetime.now(UTC):
                    left = (k.cooldown_until - datetime.now(UTC)).total_seconds()
                    detail += f" [Cooldown: {left:.1f}s remaining]"
                diagnostics.append(detail)

            diag_msg = "; ".join(diagnostics)
            raise YouTubeAPIUnavailableError(
                f"All {len(self._keys)} YouTube API keys are unavailable. Diagnostics: {diag_msg}"
            )

    async def report_success(self, label: str, operation: str = "") -> None:
        async with self._lock:
            for k in self._keys:
                if k.label == label:
                    k.mark_success(operation)
                    break

    async def report_failure(
        self,
        label: str,
        status_code: int,
        reason: str,
        message: str,
        domain: str = "",
        operation: str = "",
    ) -> None:
        async with self._lock:
            for k in self._keys:
                if k.label == label:
                    k.mark_failure(
                        status_code=status_code,
                        reason=reason,
                        message=message,
                        domain=domain,
                        operation=operation,
                    )
                    break

    async def diagnose_all_keys(
        self,
        client: httpx.AsyncClient | None = None,
        test_channel_id: str = "UCGH_osSgL2FCsBYe6XMxlSQ",
    ) -> list[dict[str, Any]]:
        """
        Direct diagnostic test: Independently tests every configured key against channels.list.
        Safe and non-destructive (1 quota unit per key).
        """
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        results = []
        url = "https://www.googleapis.com/youtube/v3/channels"

        try:
            for k in self._keys:
                label = k.label
                api_key = k.key
                params = {"part": "id", "id": test_channel_id, "key": api_key}

                try:
                    resp = await client.get(url, params=params)
                    status_code = resp.status_code

                    if status_code == 200:
                        k.mark_success("channels.list (diagnostic)")
                        results.append(
                            {
                                "label": label,
                                "status": "READY",
                                "http_code": 200,
                                "reason": "OK",
                                "message": "API key functional and valid.",
                            }
                        )
                    else:
                        err_json = {}
                        with contextlib.suppress(Exception):
                            err_json = resp.json().get("error", {})

                        errors = err_json.get("errors", [])
                        reason = errors[0].get("reason", "") if errors else err_json.get("status", "")
                        msg = err_json.get("message", resp.text[:200])
                        domain = errors[0].get("domain", "") if errors else ""

                        k.mark_failure(
                            status_code=status_code,
                            reason=reason,
                            message=msg,
                            domain=domain,
                            operation="channels.list (diagnostic)",
                        )

                        results.append(
                            {
                                "label": label,
                                "status": k.state.value,
                                "http_code": status_code,
                                "reason": reason,
                                "message": msg,
                            }
                        )

                except httpx.RequestError as e:
                    k.mark_failure(
                        status_code=0,
                        reason="NetworkError",
                        message=str(e),
                        operation="channels.list (diagnostic)",
                    )
                    results.append(
                        {
                            "label": label,
                            "status": "NETWORK_ERROR",
                            "http_code": 0,
                            "reason": "NetworkError",
                            "message": str(e),
                        }
                    )
        finally:
            if should_close:
                await client.aclose()

        return results


class OAuthManager:
    """Manages persistent Google OAuth 2.0 credentials and token refresh with lock protection."""

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        access_token: str | None,
        refresh_token: str | None,
    ) -> None:
        self.client_id = client_id.strip() if client_id else None
        self.client_secret = client_secret.strip() if client_secret else None
        self._access_token = access_token.strip() if access_token else None
        self._refresh_token = refresh_token.strip() if refresh_token else None
        self._expires_at: datetime | None = (
            datetime.now(UTC) + timedelta(seconds=3600) if self._access_token else None
        )
        self._lock = asyncio.Lock()
        self.is_reauth_required: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self._refresh_token or self._access_token)

    async def get_valid_token(self, client: httpx.AsyncClient | None = None) -> str:
        """Get a valid access token, refreshing if expired or expiring soon."""
        if not self.is_configured:
            raise YouTubeOAuthError("OAuth credentials are not configured.")

        if self.is_reauth_required:
            raise YouTubeOAuthError("OAUTH_REAUTH_REQUIRED: Refresh token is invalid or revoked.")

        now = datetime.now(UTC)
        # Refresh if token expires in less than 60 seconds or is not set
        needs_refresh = (
            self._access_token is None
            or self._expires_at is None
            or self._expires_at - now < timedelta(seconds=60)
        )

        if not needs_refresh and self._access_token is not None:
            return self._access_token

        async with self._lock:
            now = datetime.now(UTC)
            if (
                self._access_token is not None
                and self._expires_at is not None
                and self._expires_at - now >= timedelta(seconds=60)
            ):
                return self._access_token

            return await self._refresh_token_internal(client)

    async def _refresh_token_internal(self, client: httpx.AsyncClient | None = None) -> str:
        """Perform OAuth token refresh."""
        if not self._refresh_token:
            if self._access_token:
                logger.warning(
                    "No refresh token configured; using existing access token without expiry validation."
                )
                return self._access_token
            raise YouTubeOAuthError("Cannot refresh token: YOUTUBE_OAUTH_REFRESH_TOKEN is missing.")

        if not self.client_id or not self.client_secret:
            raise YouTubeOAuthError("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing for OAuth refresh.")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=15.0)
            should_close_client = True

        try:
            logger.info("Refreshing YouTube OAuth access token...")
            resp = await client.post(token_url, data=data)
            if resp.status_code == 200:
                result = resp.json()
                self._access_token = result.get("access_token")
                expires_in = result.get("expires_in", 3600)
                self._expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
                self.is_reauth_required = False
                logger.info(f"YouTube OAuth token refreshed successfully (expires in {expires_in}s).")
                assert self._access_token is not None
                return self._access_token
            elif resp.status_code in (400, 401):
                err_body = resp.text
                if "invalid_grant" in err_body:
                    self.is_reauth_required = True
                    logger.error(f"OAUTH_REAUTH_REQUIRED: Invalid refresh token ({err_body})")
                raise YouTubeOAuthError(f"OAuth refresh failed ({resp.status_code}): {err_body}")
            else:
                raise YouTubeOAuthError(f"OAuth refresh failed with status {resp.status_code}")
        except Exception as e:
            if not isinstance(e, YouTubeOAuthError):
                logger.error(f"Exception during OAuth token refresh: {e}")
                raise YouTubeOAuthError(f"OAuth refresh exception: {e}") from e
            raise
        finally:
            if should_close_client:
                await client.aclose()


class YouTubeClient:
    """High-level asynchronous YouTube Data API v3 client."""

    def __init__(
        self,
        key_pool: YouTubeKeyPool | None = None,
        oauth_manager: OAuthManager | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.key_pool = key_pool or YouTubeKeyPool(settings.get_youtube_keys())
        self.oauth = oauth_manager or OAuthManager(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            access_token=settings.YOUTUBE_OAUTH_TOKEN,
            refresh_token=settings.YOUTUBE_OAUTH_REFRESH_TOKEN,
        )
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    # -----------------------------------------------------------------------
    # Read Operations (Using YouTubeKeyPool with Forensic Error Diagnostics)
    # -----------------------------------------------------------------------

    async def _execute_read_request(
        self,
        operation_name: str,
        url: str,
        params: dict[str, Any],
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GET request rotating through the YouTubeKeyPool.
        Captures full diagnostic information for each key attempt without masking real API errors.
        """
        client = await self._get_client()
        total_keys = max(self.key_pool.total_keys, 1)
        retries_limit = max_retries if max_retries is not None else total_keys
        attempts = 0

        while attempts < retries_limit:
            attempts += 1
            try:
                label, api_key = await self.key_pool.get_next_key()
            except YouTubeAPIUnavailableError:
                # No more keys available in this cycle
                break

            req_params = {**params, "key": api_key}
            logger.debug(
                f"Executing YouTube read '{operation_name}' using key slot [{label}] (attempt {attempts}/{retries_limit})"
            )

            try:
                resp = await client.get(url, params=req_params)
                status_code = resp.status_code

                if status_code == 200:
                    await self.key_pool.report_success(label, operation=operation_name)
                    return resp.json()

                # Parse JSON error payload
                err_json: dict[str, Any] = {}
                with contextlib.suppress(Exception):
                    err_json = resp.json().get("error", {})

                errors_list = err_json.get("errors", [])
                reason = errors_list[0].get("reason", "") if errors_list else err_json.get("status", "")
                message = err_json.get("message", resp.text[:200])
                domain = errors_list[0].get("domain", "") if errors_list else ""

                logger.warning(
                    f"YouTube API read failed on [{label}]:\n"
                    f"  Operation: {operation_name}\n"
                    f"  Status: HTTP {status_code}\n"
                    f"  Reason: {reason}\n"
                    f"  Message: {message}"
                )

                await self.key_pool.report_failure(
                    label=label,
                    status_code=status_code,
                    reason=reason,
                    message=message,
                    domain=domain,
                    operation=operation_name,
                )

                # Rotate to next key
                continue

            except httpx.RequestError as e:
                logger.warning(f"Network error on [{label}] during '{operation_name}': {e}")
                await self.key_pool.report_failure(
                    label=label,
                    status_code=0,
                    reason="NetworkError",
                    message=str(e),
                    operation=operation_name,
                )
                continue

        # If loop finishes without returning, raise forensic unavailable error
        raise YouTubeAPIUnavailableError(
            f"Exhausted all available YouTube API keys for operation '{operation_name}' after {attempts} attempt(s)."
        )

    async def get_channel_details(self, channel_id: str) -> dict[str, Any] | None:
        """Fetch channel metadata (snippet, statistics) using 1 quota unit."""
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id,
        }
        try:
            data = await self._execute_read_request("channels.list", url, params)
            items = data.get("items", [])
            if items:
                return items[0]
            logger.info(f"Channel {channel_id} not found in YouTube Data API.")
            return None
        except Exception as e:
            logger.error(f"Error fetching channel details for {channel_id}: {e}")
            return None

    async def get_active_live_video(self, channel_id: str) -> dict[str, Any] | None:
        """Find the currently active live broadcast for a channel."""
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "eventType": "live",
            "type": "video",
            "maxResults": 1,
        }
        try:
            data = await self._execute_read_request("search.list(live)", url, params)
            items = data.get("items", [])
            if items:
                video_id = items[0]["id"]["videoId"]
                title = items[0]["snippet"]["title"]
                logger.info(
                    f"Active live broadcast detected for channel {channel_id}: video_id={video_id} title='{title}'"
                )
                return {"video_id": video_id, "title": title}
            return None
        except Exception as e:
            logger.error(f"Error fetching active live video for channel {channel_id}: {e}")
            return None

    async def get_live_chat_id(self, video_id: str) -> str | None:
        """Resolve activeLiveChatId for a live video ID."""
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "liveStreamingDetails,snippet",
            "id": video_id,
        }
        try:
            data = await self._execute_read_request("videos.list(liveStreamingDetails)", url, params)
            items = data.get("items", [])
            if items:
                streaming_details = items[0].get("liveStreamingDetails", {})
                chat_id = streaming_details.get("activeLiveChatId")
                if chat_id:
                    logger.info(f"Resolved activeLiveChatId for video {video_id}: {chat_id}")
                    return chat_id
                logger.info(f"Video {video_id} has liveStreamingDetails but no activeLiveChatId.")
            return None
        except Exception as e:
            logger.error(f"Error fetching liveChatId for video {video_id}: {e}")
            return None

    async def poll_chat_messages(
        self,
        live_chat_id: str,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        """
        Poll messages from live chat.
        Returns (messages_list, next_page_token, polling_interval_millis).
        """
        url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
        params: dict[str, Any] = {
            "liveChatId": live_chat_id,
            "part": "snippet,authorDetails",
            "maxResults": 200,
        }
        if page_token:
            params["pageToken"] = page_token

        data = await self._execute_read_request("liveChatMessages.list", url, params)
        items = data.get("items", [])
        next_token = data.get("nextPageToken")
        polling_interval = data.get("pollingIntervalMillis", 5000)

        return items, next_token, polling_interval

    # -----------------------------------------------------------------------
    # Authenticated Write Operations (Using OAuthManager)
    # -----------------------------------------------------------------------

    async def post_chat_message(self, live_chat_id: str, message_text: str) -> dict[str, Any] | None:
        """Send a live chat message using the authenticated bot account."""
        client = await self._get_client()
        token = await self.oauth.get_valid_token(client)
        url = "https://www.googleapis.com/youtube/v3/liveChat/messages?part=snippet"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {
                    "messageText": message_text,
                },
            }
        }
        try:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                logger.info(f"Posted chat message to {live_chat_id}: {message_text[:40]}...")
                return resp.json()
            logger.error(f"Failed to post chat message ({resp.status_code}): {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Exception posting chat message: {e}")
            return None

    async def delete_chat_message(self, live_chat_message_id: str) -> bool:
        """Delete a live chat message by message ID."""
        client = await self._get_client()
        token = await self.oauth.get_valid_token(client)
        url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"id": live_chat_message_id}

        try:
            resp = await client.delete(url, headers=headers, params=params)
            if resp.status_code in (200, 204):
                logger.info(f"Deleted live chat message {live_chat_message_id}")
                return True
            logger.error(f"Failed to delete chat message ({resp.status_code}): {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Exception deleting chat message: {e}")
            return False

    async def timeout_user(
        self,
        live_chat_id: str,
        youtube_user_id: str,
        duration_seconds: int = 300,
    ) -> bool:
        """Temporarily timeout a user from the live chat."""
        client = await self._get_client()
        token = await self.oauth.get_valid_token(client)
        url = "https://www.googleapis.com/youtube/v3/liveChat/bans?part=snippet"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "temporary",
                "banDurationSeconds": duration_seconds,
                "bannedAuthor": {
                    "channelId": youtube_user_id,
                },
            }
        }
        try:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"Timed out user {youtube_user_id} for {duration_seconds}s in {live_chat_id}")
                return True
            logger.error(f"Failed to timeout user ({resp.status_code}): {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Exception timing out user: {e}")
            return False

    async def hide_user(self, live_chat_id: str, youtube_user_id: str) -> bool:
        """Permanently hide a user from the live chat."""
        client = await self._get_client()
        token = await self.oauth.get_valid_token(client)
        url = "https://www.googleapis.com/youtube/v3/liveChat/bans?part=snippet"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "permanent",
                "bannedAuthor": {
                    "channelId": youtube_user_id,
                },
            }
        }
        try:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"Permanently hid user {youtube_user_id} from {live_chat_id}")
                return True
            logger.error(f"Failed to hide user ({resp.status_code}): {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Exception hiding user: {e}")
            return False
