"""
Asynchronous YouTube Data API v3 Client for GODDESS AI 2.0.

Provides robust, quota-aware HTTP communication with YouTube Data API v3 endpoints,
supporting automatic credential rotation on quota limits and mockable transport.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
import httpx

from app.core.logging import get_logger
from app.core.provider_errors import classify_provider_error, sanitize_error_message
from app.services.youtube.credentials import YouTubeCredentialManager, youtube_credentials
from app.services.youtube.exceptions import (
    ChatMessageValidationError,
    LiveChatUnavailableError,
    QuotaExceededError,
    RateLimitError,
    StreamNotFoundError,
    YouTubeAPIError,
)
from app.services.youtube.models import ChatMessage, LiveStreamInfo, StreamStatus

logger = get_logger("youtube.client")

BASE_API_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIClient:
    """Async API Client for YouTube Data API v3."""

    def __init__(
        self,
        credential_manager: Optional[YouTubeCredentialManager] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 3,
    ):
        self.credentials = credential_manager or youtube_credentials
        self._http_client = http_client
        self.max_retries = max_retries

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(timeout=10.0)

    async def _execute_with_rotation(
        self,
        api_method: Callable[[httpx.AsyncClient, str, Dict[str, Any]], Any],
        endpoint: str,
        params: Dict[str, Any],
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an API request with automatic credential rotation upon 403 Quota or 429 RateLimit errors.
        """
        attempts = 0
        last_exception: Optional[Exception] = None

        while attempts < self.max_retries:
            attempts += 1
            key_id, raw_key = self.credentials.get_credential()

            request_params = params.copy()
            request_params["key"] = raw_key

            client = await self._get_client()
            try:
                if json_data is not None:
                    response = await client.post(f"{BASE_API_URL}/{endpoint}", params=request_params, json=json_data)
                else:
                    response = await client.get(f"{BASE_API_URL}/{endpoint}", params=request_params)

                if response.status_code == 200:
                    await self.credentials.mark_success(key_id)
                    return response.json()

                # Handle Quota and Rate Limit Errors
                error_json = {}
                try:
                    error_json = response.json().get("error", {})
                except Exception:
                    pass

                raw_msg = error_json.get("message", response.text)
                sanitized_msg = sanitize_error_message(raw_msg)
                errors_list = error_json.get("errors", [])
                reason = errors_list[0].get("reason", "") if errors_list else ""

                code, _, is_quota = classify_provider_error(sanitized_msg, response.status_code)

                if response.status_code == 403 and (is_quota or reason in ["quotaExceeded", "dailyLimitExceeded"]):
                    await self.credentials.mark_failed(key_id, sanitized_msg, is_quota=True, status_code=403)
                    last_exception = QuotaExceededError(403, sanitized_msg, reason or "quotaExceeded")
                    logger.warning(f"Key '{key_id}' quota exceeded. Rotating to next credential...")
                    continue

                if response.status_code == 429 or reason == "rateLimitExceeded":
                    await self.credentials.mark_failed(key_id, sanitized_msg, is_quota=False, status_code=429)
                    last_exception = RateLimitError(429, sanitized_msg, reason or "rateLimitExceeded")
                    logger.warning(f"Key '{key_id}' rate limited. Rotating to next credential...")
                    continue

                if response.status_code == 404:
                    await self.credentials.mark_success(key_id)
                    raise StreamNotFoundError(f"Resource not found on YouTube: {endpoint}")

                # General API Error
                await self.credentials.mark_failed(key_id, sanitized_msg, status_code=response.status_code)
                raise YouTubeAPIError(response.status_code, sanitized_msg, reason)

            except httpx.RequestError as exc:
                sanitized_exc = sanitize_error_message(str(exc))
                await self.credentials.mark_failed(key_id, f"Network request error: {sanitized_exc}", status_code=None)
                last_exception = exc
                logger.warning(f"Network error with key '{key_id}': {sanitized_exc}. Retrying...")

        if last_exception:
            raise last_exception
        raise YouTubeAPIError(500, "Failed to execute YouTube API request after all retry attempts.")

    async def get_live_stream_details(self, stream_id: str) -> Optional[LiveStreamInfo]:
        """
        Fetch details for a live stream / video by ID.
        """
        params = {
            "part": "snippet,liveStreamingDetails,statistics",
            "id": stream_id,
        }
        data = await self._execute_with_rotation(None, "videos", params)
        items = data.get("items", [])
        if not items:
            return None

        item = items[0]
        snippet = item.get("snippet", {})
        live_details = item.get("liveStreamingDetails", {})

        live_chat_id = live_details.get("activeLiveChatId")
        concurrent_viewers = int(live_details.get("concurrentViewers", 0))

        # Determine status
        live_broadcast_content = snippet.get("liveBroadcastContent", "none")
        if live_broadcast_content == "live":
            status = StreamStatus.LIVE
        elif live_broadcast_content == "upcoming":
            status = StreamStatus.STANDBY
        elif live_details.get("actualEndTime"):
            status = StreamStatus.ENDED
        else:
            status = StreamStatus.STANDBY

        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = thumbnails.get("medium", {}).get("url") or thumbnails.get("default", {}).get("url")

        return LiveStreamInfo(
            stream_id=stream_id,
            channel_id=snippet.get("channelId", ""),
            title=snippet.get("title", "Untitled Live Stream"),
            status=status,
            concurrent_viewers=concurrent_viewers,
            live_chat_id=live_chat_id,
            scheduled_start_time=live_details.get("scheduledStartTime"),
            actual_start_time=live_details.get("actualStartTime"),
            actual_end_time=live_details.get("actualEndTime"),
            thumbnail_url=thumbnail_url,
        )

    async def get_live_chat_messages(
        self, live_chat_id: str, page_token: Optional[str] = None
    ) -> Tuple[List[ChatMessage], Optional[str], int]:
        """
        Fetch new live chat messages for an active live chat ID.
        Returns (messages_list, next_page_token, polling_interval_millis).
        """
        if not live_chat_id:
            raise LiveChatUnavailableError("No live_chat_id provided.")

        params: Dict[str, Any] = {
            "part": "snippet,authorDetails",
            "liveChatId": live_chat_id,
            "maxResults": 200,
        }
        if page_token:
            params["pageToken"] = page_token

        data = await self._execute_with_rotation(None, "liveChat/messages", params)

        polling_interval = int(data.get("pollingIntervalMillis", 4000))
        next_page_token = data.get("nextPageToken")
        items = data.get("items", [])

        normalized_messages: List[ChatMessage] = []
        for item in items:
            snippet = item.get("snippet", {})
            author = item.get("authorDetails", {})

            # Extract message text based on type
            msg_type = snippet.get("type", "textMessageEvent")
            text = ""
            is_super_chat = False
            super_chat_amount = None

            if msg_type == "textMessageEvent":
                text = snippet.get("displayMessage", "")
            elif msg_type == "superChatEvent":
                is_super_chat = True
                super_chat_details = snippet.get("superChatDetails", {})
                super_chat_amount = super_chat_details.get("amountDisplayString")
                text = super_chat_details.get("userComment", "") or snippet.get("displayMessage", "")
            else:
                text = snippet.get("displayMessage", "")

            msg = ChatMessage(
                message_id=item.get("id", ""),
                stream_id=snippet.get("liveChatId", live_chat_id),
                channel_id=author.get("channelId", ""),
                author_id=author.get("channelId", ""),
                author_name=author.get("displayName", "Anonymous"),
                author_avatar_url=author.get("profileImageUrl"),
                message_text=text,
                published_at=snippet.get("publishedAt", ""),
                is_chat_owner=author.get("isChatOwner", False),
                is_chat_moderator=author.get("isChatModerator", False),
                is_chat_sponsor=author.get("isChatSponsor", False),
                is_super_chat=is_super_chat,
                super_chat_amount=super_chat_amount,
            )
            normalized_messages.append(msg)

        return normalized_messages, next_page_token, polling_interval

    async def send_chat_message(self, live_chat_id: str, message_text: str) -> ChatMessage:
        """
        Send a text message to a YouTube live chat.
        Validates message length (1 - 200 chars).
        """
        if not message_text or not message_text.strip():
            raise ChatMessageValidationError("Message text cannot be empty.")

        cleaned_text = message_text.strip()
        if len(cleaned_text) > 200:
            raise ChatMessageValidationError(f"Message exceeds YouTube's 200 character limit ({len(cleaned_text)} chars).")

        params = {"part": "snippet"}
        json_data = {
            "snippet": {
                "liveChatId": live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {
                    "messageText": cleaned_text,
                },
            }
        }

        data = await self._execute_with_rotation(None, "liveChat/messages", params, json_data=json_data)
        snippet = data.get("snippet", {})
        author = data.get("authorDetails", {})

        return ChatMessage(
            message_id=data.get("id", ""),
            stream_id=live_chat_id,
            channel_id=author.get("channelId", ""),
            author_id=author.get("channelId", ""),
            author_name=author.get("displayName", "Bot"),
            message_text=cleaned_text,
            published_at=snippet.get("publishedAt", ""),
            is_chat_owner=author.get("isChatOwner", False),
            is_chat_moderator=author.get("isChatModerator", True),
        )


# Global singleton instance of YouTubeAPIClient
youtube_client = YouTubeAPIClient()
