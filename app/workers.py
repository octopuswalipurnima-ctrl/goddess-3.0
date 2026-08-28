"""Background workers: Stream discovery, dedicated per-stream ChatWorker, and Outbound message queue."""

import asyncio
import contextlib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select

from app.commands import CommandContext, get_user_permission, registry
from app.config import settings
from app.database import get_session
from app.economy import process_message_reward
from app.gemini import GeminiClient
from app.models import (
    ChannelSettings,
    ChatMessage,
    OneVOneQueueEntry,
    Stream,
)
from app.moderation import ModerationEngine
from app.utils import get_logger, normalize_text
from app.youtube import YouTubeClient

logger = get_logger("goddess.workers")


class OutboundMessageQueue:
    """Bounded, priority-aware outgoing live chat message queue to prevent flooding."""

    def __init__(self, youtube_client: YouTubeClient, max_queue_size: int = 50) -> None:
        self.youtube = youtube_client
        self._queue: asyncio.Queue[tuple[int, str, str]] = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._last_sent_at: float = 0.0
        self._min_interval: float = 1.5  # Seconds between outgoing messages

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

    async def enqueue(self, live_chat_id: str, message: str, priority: int = 10) -> bool:
        """
        Enqueue an outgoing chat message.
        Priority: lower integer = higher priority (e.g. 1 = moderation, 10 = cohost).
        """
        if not live_chat_id or not message:
            return False

        try:
            if self._queue.full():
                logger.warning("Outgoing message queue is full. Dropping message.")
                return False
            await self._queue.put((priority, live_chat_id, message))
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return False

    async def _process_queue(self) -> None:
        while self._running:
            try:
                priority, live_chat_id, msg_text = await self._queue.get()
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_sent_at
                if elapsed < self._min_interval:
                    await asyncio.sleep(self._min_interval - elapsed)

                await self.youtube.post_chat_message(live_chat_id, msg_text)
                self._last_sent_at = asyncio.get_event_loop().time()
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in outbound message worker: {e}")
                await asyncio.sleep(1.0)


class ChatWorker:
    """Dedicated asynchronous worker for a single live stream's chat."""

    def __init__(
        self,
        channel_id: str,
        video_id: str,
        live_chat_id: str,
        stream_id: int,
        youtube_client: YouTubeClient,
        gemini_client: GeminiClient,
        outbound_queue: OutboundMessageQueue,
    ) -> None:
        self.channel_id = channel_id
        self.video_id = video_id
        self.live_chat_id = live_chat_id
        self.stream_id = stream_id
        self.youtube = youtube_client
        self.gemini = gemini_client
        self.outbound = outbound_queue
        self.moderation_engine = ModerationEngine(gemini_client, youtube_client)

        self._running: bool = False
        self._task: asyncio.Task[None] | None = None
        self._seen_messages: set[str] = set()  # In-memory deduplication cache
        self._last_cohost_reply_at: float = 0.0
        self._recent_chat_buffer: list[dict[str, str]] = []

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            logger.info(f"Started ChatWorker for channel={self.channel_id} video={self.video_id}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info(f"Stopped ChatWorker for channel={self.channel_id} video={self.video_id}")

    async def _poll_loop(self) -> None:
        next_page_token: str | None = None
        consecutive_errors = 0

        while self._running:
            try:
                (
                    items,
                    next_page_token,
                    polling_interval,
                ) = await self.youtube.poll_chat_messages(
                    live_chat_id=self.live_chat_id,
                    page_token=next_page_token,
                )
                consecutive_errors = 0

                # Process all retrieved messages
                for item in items:
                    try:
                        await self._process_single_message(item)
                    except Exception as e:
                        logger.error(f"Error processing chat message: {e}")

                # Respect YouTube's returned polling interval (convert ms to seconds)
                sleep_seconds = max(1.0, min(30.0, polling_interval / 1000.0))
                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.warning(
                    f"Error polling chat for stream {self.stream_id} (error #{consecutive_errors}): {e}"
                )
                if consecutive_errors >= 10:
                    logger.error(f"ChatWorker for stream {self.stream_id} stopping due to repeated failures.")
                    await self._handle_stream_end()
                    break
                await asyncio.sleep(min(30.0, 3.0 * consecutive_errors))

    async def _process_single_message(self, item: dict[str, Any]) -> None:
        msg_id = item.get("id")
        if not msg_id or msg_id in self._seen_messages:
            return

        # Cache seen ID
        self._seen_messages.add(msg_id)
        if len(self._seen_messages) > 2000:
            # Keep cache bounded
            self._seen_messages = set(list(self._seen_messages)[-1000:])

        snippet = item.get("snippet", {})
        author = item.get("authorDetails", {})

        author_id = author.get("channelId", "")
        author_name = author.get("displayName", "Viewer")
        text_details = snippet.get("textMessageDetails", {})
        message_text = text_details.get("messageText", "").strip()

        if not message_text or not author_id:
            return

        norm_message = normalize_text(message_text)

        # Update in-memory context buffer
        self._recent_chat_buffer.append({"username": author_name, "message": message_text})
        if len(self._recent_chat_buffer) > 20:
            self._recent_chat_buffer = self._recent_chat_buffer[-20:]

        permission = get_user_permission(author)

        async with get_session() as session:
            # 1. Deduplication against DB
            stmt = select(ChatMessage).where(ChatMessage.youtube_message_id == msg_id)
            res = await session.execute(stmt)
            if res.scalar_one_or_none():
                return

            # Save message to DB
            chat_record = ChatMessage(
                channel_id=self.channel_id,
                stream_id=self.stream_id,
                youtube_message_id=msg_id,
                youtube_user_id=author_id,
                username=author_name,
                message=message_text,
                normalized_message=norm_message,
                created_at=datetime.now(UTC),
            )
            session.add(chat_record)
            await session.flush()

            # Load ChannelSettings
            stmt_s = select(ChannelSettings).where(ChannelSettings.channel_id == self.channel_id)
            res_s = await session.execute(stmt_s)
            ch_settings = res_s.scalar_one_or_none()
            if not ch_settings:
                ch_settings = ChannelSettings(channel_id=self.channel_id)
                session.add(ch_settings)
                await session.flush()

            # -------------------------------------------------------------------
            # Pipeline Step 1: Command Detection & Dispatch
            # -------------------------------------------------------------------
            if message_text.startswith("!"):
                ctx = CommandContext(
                    session=session,
                    channel_id=self.channel_id,
                    stream_id=self.stream_id,
                    live_chat_id=self.live_chat_id,
                    author_id=author_id,
                    author_name=author_name,
                    permission=permission,
                    channel_settings=ch_settings,
                    youtube_client=self.youtube,
                )
                cmd_reply = await registry.execute(message_text, ctx)
                if cmd_reply:
                    await self.outbound.enqueue(self.live_chat_id, cmd_reply, priority=5)
                return

            # -------------------------------------------------------------------
            # Pipeline Step 2: Moderation Check
            # -------------------------------------------------------------------
            mod_result, action_taken = await self.moderation_engine.evaluate_message(
                session=session,
                channel_id=self.channel_id,
                stream_id=self.stream_id,
                youtube_message_id=msg_id,
                youtube_user_id=author_id,
                username=author_name,
                message=message_text,
                channel_settings=ch_settings,
                recent_context=[f"@{m['username']}: {m['message']}" for m in self._recent_chat_buffer[-6:]],
            )

            # If auto-deleted, do not award economy or trigger Honney
            if action_taken in ("DELETED", "TIMED_OUT"):
                logger.info(f"Message {msg_id} was removed by moderation ({mod_result.category}).")
                return

            # -------------------------------------------------------------------
            # Pipeline Step 3: Economy (XP & Coins)
            # -------------------------------------------------------------------
            rewarded, leveled_up, new_lvl = await process_message_reward(
                session=session,
                channel_id=self.channel_id,
                youtube_user_id=author_id,
                username=author_name,
                channel_settings=ch_settings,
            )

            if leveled_up:
                level_announcement = f"🎉 @{author_name} reached Level {new_lvl}!"
                await self.outbound.enqueue(self.live_chat_id, level_announcement, priority=8)

            # -------------------------------------------------------------------
            # Pipeline Step 4: Honney AI Co-Host Wake Word Trigger
            # -------------------------------------------------------------------
            if "honney" in norm_message and ch_settings.cohost_enabled:
                now_ts = asyncio.get_event_loop().time()
                elapsed_cohost = now_ts - self._last_cohost_reply_at

                if elapsed_cohost >= ch_settings.cohost_cooldown:
                    self._last_cohost_reply_at = now_ts
                    try:
                        cohost_reply = await self.gemini.generate_cohost_response(
                            username=author_name,
                            message=message_text,
                            recent_chat=self._recent_chat_buffer,
                            personality=ch_settings.personality,
                        )
                        if cohost_reply:
                            await self.outbound.enqueue(self.live_chat_id, cohost_reply, priority=10)
                    except Exception as e:
                        logger.warning(f"Failed to generate Honney response: {e}")

    async def _handle_stream_end(self) -> None:
        """Handle stream termination and cancel waiting 1v1 entries."""
        async with get_session() as session:
            stmt = select(Stream).where(Stream.id == self.stream_id)
            res = await session.execute(stmt)
            stream = res.scalar_one_or_none()
            if stream:
                stream.status = "ENDED"
                stream.ended_at = datetime.now(UTC)

            # Cancel remaining waiting 1v1 entries
            stmt_q = select(OneVOneQueueEntry).where(
                OneVOneQueueEntry.stream_id == self.stream_id,
                OneVOneQueueEntry.status == "WAITING",
            )
            res_q = await session.execute(stmt_q)
            for entry in res_q.scalars().all():
                entry.status = "CANCELLED"

        logger.info(f"Stream {self.stream_id} marked as ENDED.")


class StreamManager:
    """Manages active live streams, resolves liveChatId, and coordinates ChatWorkers."""

    def __init__(
        self,
        youtube_client: YouTubeClient,
        gemini_client: GeminiClient,
        outbound_queue: OutboundMessageQueue,
    ) -> None:
        self.youtube = youtube_client
        self.gemini = gemini_client
        self.outbound = outbound_queue
        self._workers: dict[str, ChatWorker] = {}  # channel_id -> ChatWorker
        self._lock = asyncio.Lock()
        self._discovery_task: asyncio.Task[None] | None = None
        self._running: bool = False

    def start(self) -> None:
        if not self._running:
            self._running = True
            self.outbound.start()
            self._discovery_task = asyncio.create_task(self._periodic_discovery_loop())
            logger.info("StreamManager started.")

    async def stop(self) -> None:
        self._running = False
        if self._discovery_task:
            self._discovery_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._discovery_task

        async with self._lock:
            for worker in self._workers.values():
                await worker.stop()
            self._workers.clear()

        await self.outbound.stop()
        logger.info("StreamManager stopped.")

    async def on_video_detected(self, channel_id: str, video_id: str) -> None:
        """Called by WebSub when a video notification is received."""
        logger.info(f"WebSub notification for channel={channel_id} video={video_id}")
        await self._check_and_start_stream(channel_id, video_id)

    async def _check_and_start_stream(self, channel_id: str, video_id: str, title: str | None = None) -> None:
        """Resolve liveChatId and start ChatWorker if not already running."""
        async with self._lock:
            if (
                channel_id in self._workers
                and self._workers[channel_id]._running
                and self._workers[channel_id].video_id == video_id
            ):
                return

            # Resolve liveChatId
            live_chat_id = await self.youtube.get_live_chat_id(video_id)
            if not live_chat_id:
                logger.info(f"Video {video_id} does not have an active live chat. Not a live stream.")
                return

            logger.info(
                f"STREAM DETECTED:\n"
                f"  Channel ID: {channel_id}\n"
                f"  Video ID: {video_id}\n"
                f"  Live Chat ID: {live_chat_id}\n"
                f"  Chat Worker: STARTING"
            )

            # Persist or update Stream in DB
            async with get_session() as session:
                stmt = select(Stream).where(
                    Stream.channel_id == channel_id,
                    Stream.youtube_video_id == video_id,
                )
                res = await session.execute(stmt)
                stream = res.scalar_one_or_none()

                if not stream:
                    stream = Stream(
                        channel_id=channel_id,
                        youtube_video_id=video_id,
                        live_chat_id=live_chat_id,
                        title=title,
                        status="LIVE",
                        started_at=datetime.now(UTC),
                        created_at=datetime.now(UTC),
                    )
                    session.add(stream)
                    await session.flush()
                else:
                    stream.live_chat_id = live_chat_id
                    stream.status = "LIVE"
                    stream.updated_at = datetime.now(UTC)

                stream_id = stream.id

            # Stop existing worker if running for different video
            if channel_id in self._workers:
                await self._workers[channel_id].stop()

            # Start new worker
            worker = ChatWorker(
                channel_id=channel_id,
                video_id=video_id,
                live_chat_id=live_chat_id,
                stream_id=stream_id,
                youtube_client=self.youtube,
                gemini_client=self.gemini,
                outbound_queue=self.outbound,
            )
            self._workers[channel_id] = worker
            worker.start()
            logger.info(f"Chat Worker STARTED for stream {stream_id} (video={video_id})")

    async def _periodic_discovery_loop(self) -> None:
        """Periodic safety net to discover active live streams with exponential backoff on errors."""
        backoff_seconds = 60.0
        while self._running:
            try:
                # Check if at least one YouTube key is ready
                if self.youtube.key_pool.get_healthy_count() == 0:
                    logger.warning(
                        "Periodic stream discovery skipped: All YouTube API keys are in cooldown/unavailable."
                    )
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds = min(backoff_seconds * 1.5, 300.0)
                    continue

                channels = settings.load_channels()
                any_checked = False
                for ch in channels:
                    if not self._running:
                        break
                    # If already active worker, skip polling search
                    if ch.channel_id in self._workers and self._workers[ch.channel_id]._running:
                        continue

                    # Search active live stream
                    any_checked = True
                    live_info = await self.youtube.get_active_live_video(ch.channel_id)
                    if live_info:
                        vid = live_info.get("video_id")
                        title = live_info.get("title")
                        if vid:
                            await self._check_and_start_stream(ch.channel_id, vid, title)

                # If successful check, reset backoff to normal 120s interval
                if any_checked:
                    backoff_seconds = 60.0
                await asyncio.sleep(120.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(
                    f"Error in periodic stream discovery loop (backoff {backoff_seconds:.0f}s): {e}"
                )
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 1.5, 300.0)


# ---------------------------------------------------------------------------
# WebSub Manager (PubSubHubbub Subscriptions & Renewals)
# ---------------------------------------------------------------------------


class WebSubManager:
    """Manages WebSub/PubSubHubbub topic subscriptions for all configured channels."""

    HUB_URL = "https://pubsubhubbub.appspot.com/"
    TOPIC_BASE = "https://www.youtube.com/xml/feeds/videos.xml?channel_id="

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client
        self._running: bool = False
        self._task: asyncio.Task[None] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._subscription_loop())
            logger.info("WebSubManager started.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        logger.info("WebSubManager stopped.")

    async def subscribe_channel(self, channel_id: str) -> bool:
        """Send subscription request to Google PubSubHubbub hub."""
        if not settings.WEBSUB_CALLBACK_URL:
            logger.warning("WEBSUB_CALLBACK_URL not set; skipping WebSub subscription.")
            return False

        topic_url = f"{self.TOPIC_BASE}{channel_id}"
        client = await self._get_client()

        data = {
            "hub.callback": settings.WEBSUB_CALLBACK_URL,
            "hub.mode": "subscribe",
            "hub.topic": topic_url,
            "hub.secret": settings.WEBSUB_SECRET,
            "hub.lease_seconds": "864000",  # 10 days
        }

        try:
            resp = await client.post(self.HUB_URL, data=data)
            if resp.status_code in (202, 204):
                logger.info(
                    f"WebSub subscription request accepted (status={resp.status_code}) for channel {channel_id}"
                )
                return True
            logger.warning(f"WebSub subscription returned {resp.status_code}: {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Error subscribing to WebSub for channel {channel_id}: {e}")
            return False

    async def _subscription_loop(self) -> None:
        """Periodic loop to ensure all active channels are subscribed."""
        while self._running:
            try:
                channels = settings.load_channels()
                for ch in channels:
                    await self.subscribe_channel(ch.channel_id)
                # Check / renew every 24 hours
                await asyncio.sleep(86400.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSub subscription loop: {e}")
                await asyncio.sleep(3600.0)


def parse_websub_xml_feed(xml_content: str | bytes) -> tuple[str | None, str | None]:
    """
    Parse YouTube Atom XML feed notification.
    Returns (channel_id, video_id).
    """
    try:
        root = ET.fromstring(xml_content)
        # Namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        # Check for deleted entry
        deleted_entry = root.find("atom:deleted-entry", ns)
        if deleted_entry is not None:
            return None, None

        entry = root.find("atom:entry", ns)
        if entry is None:
            return None, None

        video_id_elem = entry.find("yt:videoId", ns)
        channel_id_elem = entry.find("yt:channelId", ns)

        video_id = video_id_elem.text if video_id_elem is not None else None
        channel_id = channel_id_elem.text if channel_id_elem is not None else None

        return channel_id, video_id
    except Exception as e:
        logger.warning(f"Failed to parse WebSub XML feed: {e}")
        return None, None
