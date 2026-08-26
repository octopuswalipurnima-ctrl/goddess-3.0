"""YouTube Data API v3 Client with 3-key pool rotation and persistent OAuth2 manager."""

import asyncio
import random
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.config import settings
from app.utils import get_logger

logger = get_logger("goddess.youtube")


class YouTubeAPIUnavailableError(Exception):
    """Raised when all YouTube API keys in the pool are exhausted or in cooldown."""


class YouTubeOAuthError(Exception):
    """Raised when OAuth authentication or refresh fails."""


class YouTubeKeyItem:
    """Tracks state and cooldown for a single YouTube Data API key."""

    def __init__(self, label: str, key: str) -> None:
        self.label = label
        self.key = key
        self.is_healthy: bool = True
        self.cooldown_until: datetime | None = None
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_used: datetime | None = None
        self.last_error: str | None = None

    def is_available(self) -> bool:
        """Check if key is ready for requests."""
        if not self.is_healthy:
            return False
        if self.cooldown_until is not None:
            if datetime.now(UTC) < self.cooldown_until:
                return False
            # Cooldown expired, restore health
            self.cooldown_until = None
        return True

    def mark_success(self) -> None:
        """Update metrics on successful call."""
        self.success_count += 1
        self.failure_count = 0
        self.cooldown_until = None
        self.last_used = datetime.now(UTC)
        self.last_error = None

    def mark_failure(self, error_msg: str, status_code: int = 0) -> None:
        """Apply exponential backoff cooldown with jitter upon error."""
        self.failure_count += 1
        self.last_error = error_msg
        self.last_used = datetime.now(UTC)

        # Base cooldown: 30 seconds * 2^(failure_count - 1), max 15 minutes, with jitter
        base_seconds = min(30 * (2 ** (self.failure_count - 1)), 900)
        jitter = random.uniform(0.8, 1.2)
        cooldown_duration = timedelta(seconds=base_seconds * jitter)
        self.cooldown_until = datetime.now(UTC) + cooldown_duration

        logger.warning(
            f"YouTube key {self.label} marked for cooldown "
            f"({cooldown_duration.total_seconds():.1f}s) due to error (code={status_code}): {error_msg}"
        )


class YouTubeKeyPool:
    """Thread-safe round-robin pool for 3 YouTube Data API keys."""

    def __init__(self, keys: list[str]) -> None:
        self._keys: list[YouTubeKeyItem] = [
            YouTubeKeyItem(f"youtube-key-{i + 1}", key) for i, key in enumerate(keys)
        ]
        self._index: int = 0
        self._lock = asyncio.Lock()

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    def get_healthy_count(self) -> int:
        return sum(1 for k in self._keys if k.is_available())

    async def get_next_key(self) -> tuple[str, str]:
        """Select next available healthy key via round-robin."""
        async with self._lock:
            if not self._keys:
                raise YouTubeAPIUnavailableError("No YouTube API keys configured.")

            # Search starting from current index
            for _ in range(len(self._keys)):
                key_item = self._keys[self._index]
                self._index = (self._index + 1) % len(self._keys)
                if key_item.is_available():
                    return key_item.label, key_item.key

            # Check if any key is closest to waking up
            raise YouTubeAPIUnavailableError("All YouTube API keys are currently in cooldown or exhausted.")

    async def report_success(self, label: str) -> None:
        async with self._lock:
            for k in self._keys:
                if k.label == label:
                    k.mark_success()
                    break

    async def report_failure(self, label: str, status_code: int, error_msg: str) -> None:
        async with self._lock:
            for k in self._keys:
                if k.label == label:
                    k.mark_failure(error_msg, status_code)
                    break


class OAuthManager:
    """Manages persistent Google OAuth 2.0 credentials and token refresh with lock protection."""

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        access_token: str | None,
        refresh_token: str | None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at: datetime | None = None
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
            # Double check inside lock
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
    # Read Operations (Using YouTubeKeyPool)
    # -----------------------------------------------------------------------

    async def _execute_read_request(
        self,
        url: str,
        params: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a GET request rotating through the YouTubeKeyPool on 403/429 errors."""
        client = await self._get_client()
        attempts = 0

        while attempts < max_retries:
            attempts += 1
            label, api_key = await self.key_pool.get_next_key()
            req_params = {**params, "key": api_key}

            try:
                resp = await client.get(url, params=req_params)
                if resp.status_code == 200:
                    await self.key_pool.report_success(label)
                    return resp.json()
                elif resp.status_code in (403, 429):
                    error_data = resp.json().get("error", {})
                    reason = ""
                    if error_data.get("errors"):
                        reason = error_data["errors"][0].get("reason", "")
                    msg = f"Quota/Rate error: {reason or resp.text[:100]}"
                    await self.key_pool.report_failure(label, resp.status_code, msg)
                    logger.warning(
                        f"YouTube read call failed on {label} (attempt {attempts}/{max_retries}): {msg}"
                    )
                    continue
                else:
                    msg = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    await self.key_pool.report_failure(label, resp.status_code, msg)
                    raise httpx.HTTPStatusError(msg, request=resp.request, response=resp)

            except httpx.RequestError as e:
                await self.key_pool.report_failure(label, 0, f"Network error: {e}")
                logger.warning(f"Network error on {label}: {e}")
                continue

        raise YouTubeAPIUnavailableError("Exhausted retries across YouTube API key pool.")

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
            data = await self._execute_read_request(url, params)
            items = data.get("items", [])
            if items:
                video_id = items[0]["id"]["videoId"]
                title = items[0]["snippet"]["title"]
                return {"video_id": video_id, "title": title}
            return None
        except Exception as e:
            logger.error(f"Error fetching active live video for channel {channel_id}: {e}")
            return None

    async def get_live_chat_id(self, video_id: str) -> str | None:
        """Resolve activeLiveChatId for a live video ID."""
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "liveStreamingDetails",
            "id": video_id,
        }
        try:
            data = await self._execute_read_request(url, params)
            items = data.get("items", [])
            if items:
                streaming_details = items[0].get("liveStreamingDetails", {})
                return streaming_details.get("activeLiveChatId")
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

        data = await self._execute_read_request(url, params)
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
