"""
Live Chat Reader & Deduplication Service for GODDESS AI 2.0.

Polls YouTube Live Chat messages at provider-specified intervals, applies message
deduplication, publishes normalized events onto the Event Bus, and broadcasts to WebSockets.
"""

import asyncio
import time
from collections import OrderedDict
from typing import Optional, Set

from app.api.v1.endpoints.ws import ws_manager
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.exceptions import (
    LiveChatUnavailableError,
    StreamNotFoundError,
    YouTubeAPIError,
)
from app.services.youtube.models import ChatMessage, SessionMetrics

logger = get_logger("youtube.chat")


class LiveChatReader:
    """Async worker that reads and processes live chat messages for a single stream session."""

    def __init__(
        self,
        stream_id: str,
        live_chat_id: str,
        api_client: Optional[YouTubeAPIClient] = None,
        max_dedup_cache_size: int = 5000,
    ):
        self.stream_id = stream_id
        self.live_chat_id = live_chat_id
        self.client = api_client or youtube_client
        self.metrics = SessionMetrics()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._next_page_token: Optional[str] = None
        self._polling_interval_sec: float = 4.0

        # LRU Deduplication Cache: keeps track of recent message IDs
        self._seen_messages: OrderedDict[str, float] = OrderedDict()
        self._max_dedup_cache_size = max_dedup_cache_size

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def _is_duplicate_message(self, message_id: str) -> bool:
        """Check if message_id has already been processed."""
        if not message_id:
            return False
        if message_id in self._seen_messages:
            return True

        self._seen_messages[message_id] = time.time()
        if len(self._seen_messages) > self._max_dedup_cache_size:
            self._seen_messages.popitem(last=False)
        return False

    async def start(self) -> None:
        """Start the background live chat reader task."""
        if self.is_running:
            logger.warning(f"LiveChatReader for stream '{self.stream_id}' is already running.")
            return

        self._running = True
        self.metrics.start_time = time.time()
        self._task = asyncio.create_task(self._poll_loop(), name=f"chat-reader-{self.stream_id}")
        logger.info(f"Started LiveChatReader for stream '{self.stream_id}' (chat_id: {self.live_chat_id})")

    async def stop(self) -> None:
        """Gracefully stop the background live chat reader task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped LiveChatReader for stream '{self.stream_id}'")

    async def _poll_loop(self) -> None:
        """Main polling loop fetching messages at provider intervals with exponential backoff."""
        consecutive_errors = 0
        backoff_delay = 1.0

        await event_bus.publish("CHAT_CONNECTED", {"stream_id": self.stream_id, "live_chat_id": self.live_chat_id})

        while self._running:
            try:
                messages, next_token, interval_ms = await self.client.get_live_chat_messages(
                    self.live_chat_id, self._next_page_token
                )

                # Reset backoff on success
                consecutive_errors = 0
                backoff_delay = 1.0
                self._next_page_token = next_token
                # Clamp polling interval to safe minimum (1.0s)
                self._polling_interval_sec = max(1.0, interval_ms / 1000.0)

                # Process and dispatch new messages
                new_messages_count = 0
                for msg in messages:
                    if not self._is_duplicate_message(msg.message_id):
                        new_messages_count += 1
                        self.metrics.messages_received += 1
                        self.metrics.last_activity_time = time.time()

                        # 1. Publish internal event
                        await event_bus.publish(
                            "CHAT_MESSAGE",
                            {
                                "stream_id": self.stream_id,
                                "message": msg.model_dump(),
                            },
                        )

                        # 2. Broadcast to real-time WebSocket dashboard clients
                        await ws_manager.broadcast_json({
                            "type": "CHAT_MESSAGE",
                            "stream_id": self.stream_id,
                            "data": msg.model_dump(),
                        })

                if new_messages_count > 0:
                    logger.debug(
                        f"Stream '{self.stream_id}': Dispatched {new_messages_count} new chat message(s)."
                    )

                await asyncio.sleep(self._polling_interval_sec)

            except asyncio.CancelledError:
                break

            except (LiveChatUnavailableError, StreamNotFoundError) as e:
                logger.info(f"Stream '{self.stream_id}' live chat ended or unavailable: {e}")
                await event_bus.publish(
                    "STREAM_ENDED",
                    {"stream_id": self.stream_id, "reason": str(e)},
                )
                break

            except Exception as e:
                consecutive_errors += 1
                self.metrics.polling_errors += 1
                self.metrics.reconnect_count += 1

                # Calculate exponential backoff (capped at 30 seconds)
                backoff_delay = min(30.0, 1.0 * (2 ** min(consecutive_errors - 1, 5)))
                logger.warning(
                    f"Chat read error for stream '{self.stream_id}' (attempt {consecutive_errors}): {e}. Retrying in {backoff_delay:.1f}s..."
                )

                await event_bus.publish(
                    "YOUTUBE_ERROR",
                    {
                        "stream_id": self.stream_id,
                        "service": "chat_reader",
                        "error": str(e),
                        "retry_in": backoff_delay,
                    },
                )

                try:
                    await asyncio.sleep(backoff_delay)
                except asyncio.CancelledError:
                    break

        await event_bus.publish("CHAT_DISCONNECTED", {"stream_id": self.stream_id})
