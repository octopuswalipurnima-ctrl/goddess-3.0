"""
Isolated Stream Session Abstraction for GODDESS AI 2.0.

Encapsulates the lifecycle, metadata, metrics, and chat reader for a single YouTube live stream.
Failure in one StreamSession is strictly isolated and does not disrupt concurrent sessions.
"""

from datetime import datetime, timezone
import time
from typing import Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.provider_errors import classify_provider_error
from app.services.youtube.chat import LiveChatReader
from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.exceptions import (
    ChatMessageValidationError,
    LiveChatUnavailableError,
    StreamNotFoundError,
    YouTubeEngineError,
)
from app.services.youtube.models import (
    ChatMessage,
    LiveStreamInfo,
    SessionMetrics,
    StreamSessionSummary,
    StreamStatus,
)

logger = get_logger("youtube.session")


class StreamSession:
    """Represents an isolated YouTube live stream session."""

    def __init__(
        self,
        stream_id: str,
        channel_id: Optional[str] = None,
        api_client: Optional[YouTubeAPIClient] = None,
    ):
        self.stream_id = stream_id
        self.video_id = stream_id
        self.channel_id = channel_id
        self.client = api_client or youtube_client
        self.status = StreamStatus.STANDBY
        self.stream_info: Optional[LiveStreamInfo] = None
        self.chat_reader: Optional[LiveChatReader] = None
        self.created_at = time.time()
        self.metrics = SessionMetrics(start_time=self.created_at)

    @property
    def is_active(self) -> bool:
        return self.status in [StreamStatus.LIVE, StreamStatus.CONNECTING, StreamStatus.RECONNECTING]

    @property
    def uptime_seconds(self) -> float:
        if self.metrics.connected_at:
            return round(time.time() - self.metrics.connected_at, 1)
        elif self.metrics.start_time:
            return round(time.time() - self.metrics.start_time, 1)
        return 0.0

    async def start(self) -> None:
        """
        Connects to the YouTube stream, resolves metadata/live_chat_id, and starts live chat reader.
        """
        if self.status == StreamStatus.LIVE:
            logger.warning(f"Session '{self.stream_id}' is already LIVE.")
            return

        self.status = StreamStatus.CONNECTING
        logger.info(f"Connecting to live stream '{self.stream_id}'...")

        try:
            # 1. Fetch live stream metadata
            info = await self.client.get_live_stream_details(self.stream_id)
            if not info:
                self.status = StreamStatus.FAILED
                raise StreamNotFoundError(f"Stream '{self.stream_id}' not found on YouTube.")

            self.stream_info = info
            self.channel_id = info.channel_id or self.channel_id
            now = time.time()
            self.metrics.connected_at = now
            self.metrics.last_activity_time = now

            # 2. Check and initialize live chat if available
            if not info.live_chat_id:
                logger.warning(f"Stream '{self.stream_id}' has no active live_chat_id.")
                self.status = StreamStatus.LIVE
            else:
                self.chat_reader = LiveChatReader(
                    stream_id=self.stream_id,
                    live_chat_id=info.live_chat_id,
                    api_client=self.client,
                )
                await self.chat_reader.start()
                self.status = StreamStatus.LIVE

            logger.info(f"StreamSession '{self.stream_id}' is now LIVE: '{info.title}'")

            await event_bus.publish(
                "STREAM_CONNECTED",
                {
                    "stream_id": self.stream_id,
                    "video_id": self.video_id,
                    "channel_id": self.channel_id,
                    "title": info.title,
                    "live_chat_id": info.live_chat_id,
                    "concurrent_viewers": info.concurrent_viewers,
                },
            )

        except Exception as e:
            self.status = StreamStatus.FAILED
            code, sanitized_msg, is_quota = classify_provider_error(e)
            logger.error(f"Failed to start stream session '{self.stream_id}': {sanitized_msg}")
            await event_bus.publish(
                "YOUTUBE_ERROR",
                {
                    "stream_id": self.stream_id,
                    "service": "stream_session",
                    "error": sanitized_msg,
                    "error_type": code.value,
                    "is_quota": is_quota,
                },
            )
            raise

    async def stop(self, reason: str = "Manual stop") -> None:
        """Gracefully terminate live chat reader and mark session as ENDED."""
        logger.info(f"Stopping StreamSession '{self.stream_id}' (Reason: {reason})")
        if self.chat_reader:
            await self.chat_reader.stop()
            self.chat_reader = None

        self.status = StreamStatus.ENDED
        await event_bus.publish(
            "STREAM_ENDED",
            {
                "stream_id": self.stream_id,
                "video_id": self.video_id,
                "reason": reason,
                "uptime_seconds": self.uptime_seconds,
            },
        )

    async def send_chat_message(self, message_text: str) -> ChatMessage:
        """
        Post an outgoing message to the stream's live chat after validation and safety checks.
        """
        if not self.stream_info or not self.stream_info.live_chat_id:
            raise LiveChatUnavailableError(f"No active live chat available for stream '{self.stream_id}'.")

        if not message_text or not message_text.strip():
            raise ChatMessageValidationError("Message text cannot be empty.")

        cleaned_text = message_text.strip()
        if len(cleaned_text) > 200:
            raise ChatMessageValidationError(f"Message exceeds 200 characters limit ({len(cleaned_text)} chars).")

        msg = await self.client.send_chat_message(self.stream_info.live_chat_id, cleaned_text)
        now = time.time()
        self.metrics.messages_published += 1
        self.metrics.messages_sent += 1
        self.metrics.last_activity_time = now
        return msg

    def to_summary(self) -> StreamSessionSummary:
        """Export state summary with safe telemetry for API responses and dashboard rendering."""
        connected_at_str = (
            datetime.fromtimestamp(self.metrics.connected_at, timezone.utc).isoformat()
            if self.metrics.connected_at
            else None
        )
        last_activity_str = (
            datetime.fromtimestamp(self.metrics.last_activity_time, timezone.utc).isoformat()
            if self.metrics.last_activity_time
            else None
        )
        last_msg_str = (
            datetime.fromtimestamp(self.chat_reader.metrics.last_message_at, timezone.utc).isoformat()
            if self.chat_reader and self.chat_reader.metrics.last_message_at
            else (
                datetime.fromtimestamp(self.metrics.last_message_at, timezone.utc).isoformat()
                if self.metrics.last_message_at
                else None
            )
        )
        last_reconnect_str = (
            datetime.fromtimestamp(self.chat_reader.metrics.last_reconnect_at, timezone.utc).isoformat()
            if self.chat_reader and self.chat_reader.metrics.last_reconnect_at
            else (
                datetime.fromtimestamp(self.metrics.last_reconnect_at, timezone.utc).isoformat()
                if self.metrics.last_reconnect_at
                else None
            )
        )
        total_msgs_recv = (
            self.chat_reader.metrics.messages_received
            if self.chat_reader
            else self.metrics.messages_received
        )
        total_msgs_sent = self.metrics.messages_sent or self.metrics.messages_published
        total_reconnects = (
            self.chat_reader.metrics.reconnect_count
            if self.chat_reader
            else self.metrics.reconnect_count
        )

        return StreamSessionSummary(
            stream_id=self.stream_id,
            video_id=self.video_id,
            channel_id=self.channel_id,
            title=self.stream_info.title if self.stream_info else None,
            status=self.status,
            connection_status=self.status.value,
            live_chat_id=self.stream_info.live_chat_id if self.stream_info else None,
            concurrent_viewers=self.stream_info.concurrent_viewers if self.stream_info else 0,
            messages_received=total_msgs_recv,
            messages_sent=total_msgs_sent,
            reconnect_count=total_reconnects,
            uptime_seconds=self.uptime_seconds,
            connected_at=connected_at_str,
            last_activity=last_activity_str,
            last_message_at=last_msg_str,
            last_reconnect_at=last_reconnect_str,
            current_credential_id=getattr(self.client.credentials, "get_health_summary", lambda: [])()[0].credential_id if hasattr(self.client, "credentials") else None,
            provider_health="HEALTHY" if self.is_active else "STANDBY",
        )
