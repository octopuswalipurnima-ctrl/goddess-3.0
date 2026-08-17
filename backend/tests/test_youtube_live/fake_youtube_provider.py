"""
Deterministic Offline Fake YouTube Provider for GODDESS AI 2.0.

Provides high-fidelity offline simulation of YouTube Data API v3 endpoints,
supporting chat message generation, duplicate message delivery, credential rotation
testing, quota exhaustion injection, and network disconnect simulation with zero external calls.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import (
    ChatMessageValidationError,
    LiveChatUnavailableError,
    QuotaExceededError,
    RateLimitError,
    StreamNotFoundError,
    YouTubeAPIError,
)
from app.services.youtube.models import ChatMessage, LiveStreamInfo, StreamStatus


class FakeYouTubeProvider:
    """Deterministic in-memory mock of YouTube Live API."""

    def __init__(
        self,
        credential_manager: Optional[YouTubeCredentialManager] = None,
    ):
        self.credentials = credential_manager or YouTubeCredentialManager(
            keys=["FakeYTKey111111111111111111", "FakeYTKey222222222222222222"]
        )
        self.streams: Dict[str, LiveStreamInfo] = {}
        self.chat_queues: Dict[str, List[ChatMessage]] = {}
        self.sent_messages: List[Dict[str, Any]] = []

        # Fault Injection Flags
        self.quota_error_count = 0
        self.rate_limit_error_count = 0
        self.network_error_count = 0
        self.unavailable_error_count = 0
        self.stream_not_found_ids = set()

    def register_stream(
        self,
        stream_id: str,
        title: str = "Test Stream",
        channel_id: str = "test_channel",
        live_chat_id: Optional[str] = None,
        status: StreamStatus = StreamStatus.LIVE,
        concurrent_viewers: int = 150,
    ) -> LiveStreamInfo:
        """Register a mock live stream in the fake provider."""
        chat_id = live_chat_id or f"chat_{stream_id}"
        info = LiveStreamInfo(
            stream_id=stream_id,
            channel_id=channel_id,
            title=title,
            status=status,
            concurrent_viewers=concurrent_viewers,
            live_chat_id=chat_id,
            scheduled_start_time=datetime.now(timezone.utc).isoformat(),
            actual_start_time=datetime.now(timezone.utc).isoformat(),
        )
        self.streams[stream_id] = info
        self.chat_queues[chat_id] = []
        return info

    def queue_chat_message(
        self,
        live_chat_id: str,
        author_name: str,
        message_text: str,
        author_id: Optional[str] = None,
        message_id: Optional[str] = None,
        is_mod: bool = False,
        is_owner: bool = False,
    ) -> ChatMessage:
        """Enqueues a chat message to be returned on the next get_live_chat_messages call."""
        if live_chat_id not in self.chat_queues:
            self.chat_queues[live_chat_id] = []

        msg = ChatMessage(
            message_id=message_id or f"msg_{int(time.time() * 1000)}_{len(self.chat_queues[live_chat_id])}",
            stream_id=live_chat_id,
            channel_id="test_channel",
            author_id=author_id or f"user_{author_name.lower()}",
            author_name=author_name,
            message_text=message_text,
            published_at=datetime.now(timezone.utc).isoformat(),
            is_chat_owner=is_owner,
            is_chat_moderator=is_mod,
        )
        self.chat_queues[live_chat_id].append(msg)
        return msg

    async def get_live_stream_details(self, stream_id: str) -> Optional[LiveStreamInfo]:
        """Simulate GET /videos."""
        self._check_fault_injection()

        if stream_id in self.stream_not_found_ids or stream_id not in self.streams:
            return None

        key_id, _ = self.credentials.get_credential()
        await self.credentials.mark_success(key_id)
        return self.streams[stream_id]

    async def get_live_chat_messages(
        self, live_chat_id: str, page_token: Optional[str] = None
    ) -> Tuple[List[ChatMessage], Optional[str], int]:
        """Simulate GET /liveChat/messages."""
        self._check_fault_injection()

        key_id, _ = self.credentials.get_credential()
        await self.credentials.mark_success(key_id)

        messages = self.chat_queues.get(live_chat_id, [])
        # Drain the current queued messages
        self.chat_queues[live_chat_id] = []
        next_token = f"token_{int(time.time())}"
        return messages, next_token, 1000

    async def send_chat_message(self, live_chat_id: str, message_text: str) -> ChatMessage:
        """Simulate POST /liveChat/messages."""
        self._check_fault_injection()

        if not message_text or not message_text.strip():
            raise ChatMessageValidationError("Message text cannot be empty.")
        if len(message_text.strip()) > 200:
            raise ChatMessageValidationError(f"Message exceeds 200 characters ({len(message_text)} chars).")

        key_id, _ = self.credentials.get_credential()
        await self.credentials.mark_success(key_id)

        msg = ChatMessage(
            message_id=f"bot_msg_{int(time.time() * 1000)}",
            stream_id=live_chat_id,
            channel_id="bot_channel",
            author_id="bot_user",
            author_name="GODDESS AI",
            message_text=message_text.strip(),
            published_at=datetime.now(timezone.utc).isoformat(),
            is_chat_owner=False,
            is_chat_moderator=True,
        )
        self.sent_messages.append({"live_chat_id": live_chat_id, "message": msg})
        return msg

    def _check_fault_injection(self) -> None:
        """Evaluate and raise any configured fault injection triggers."""
        if self.quota_error_count > 0:
            self.quota_error_count -= 1
            key_id, _ = self.credentials.get_credential()
            raise QuotaExceededError(403, "The request cannot be completed because you have exceeded your quota.", "quotaExceeded")

        if self.rate_limit_error_count > 0:
            self.rate_limit_error_count -= 1
            raise RateLimitError(429, "Rate limit exceeded.", "rateLimitExceeded")

        if self.network_error_count > 0:
            self.network_error_count -= 1
            raise YouTubeAPIError(500, "Network connection timed out.", "networkError")

        if self.unavailable_error_count > 0:
            self.unavailable_error_count -= 1
            raise YouTubeAPIError(503, "YouTube backend temporarily unavailable.", "backendError")
