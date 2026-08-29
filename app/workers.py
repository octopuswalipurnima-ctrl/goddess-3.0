"""Background workers: Stream discovery, dedicated per-stream ChatWorker, and Outbound message queue."""

import asyncio
import contextlib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx
from sqlalchemy import select

from app.commands import CommandContext, get_user_permission, registry
from app.config import settings
from app.database import get_session
from app.economy import process_message_reward
from app.gemini import GeminiClient
from app.models import (
    AuditLog,
    ChannelSettings,
    ChatMessage,
    OneVOneQueueEntry,
    Stream,
)
from app.moderation import ModerationEngine
from app.utils import get_logger, normalize_text, parse_youtube_video_id
from app.youtube import LiveDetectionResult, LiveDetectionStatus, YouTubeClient

logger = get_logger("goddess.workers")


class WorkerState(StrEnum):
    """Lifecycle states for ChatWorker instances."""

    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    FAILED = "FAILED"


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
        self.state: WorkerState = WorkerState.STOPPED
        self._first_poll_done: bool = False
        self._task: asyncio.Task[None] | None = None
        self._seen_messages: set[str] = set()  # In-memory deduplication cache
        self._last_cohost_reply_at: float = 0.0
        self._recent_chat_buffer: list[dict[str, str]] = []

    def start(self) -> None:
        if not self._running:
            self._running = True
            self.state = WorkerState.STARTING
            logger.info(
                f"[CHAT WORKER]\n"
                f"  channel_id={self.channel_id}\n"
                f"  video_id={self.video_id}\n"
                f"  live_chat_id={self.live_chat_id}\n"
                f"  stream_id={self.stream_id}\n"
                f"  status=STARTING"
            )
            self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        self.state = WorkerState.STOPPING
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self.state = WorkerState.STOPPED
        logger.info(f"[CHAT WORKER] Stopped worker for channel={self.channel_id} video={self.video_id}")

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

                if not self._first_poll_done:
                    self._first_poll_done = True
                    self.state = WorkerState.RUNNING
                    logger.info(
                        f"[CHAT POLLER]\n"
                        f"  FIRST_POLL\n"
                        f"  live_chat_id={self.live_chat_id}\n"
                        f"  status=SUCCESS\n"
                        f"  messages_received={len(items)}"
                    )
                    logger.info("[CHAT WORKER] status=RUNNING")

                # Process all retrieved messages
                for item in items:
                    try:
                        await self._process_single_message(item)
                    except Exception as e:
                        logger.error(f"Error processing chat message: {e}", exc_info=True)

                # Respect YouTube's returned polling interval (convert ms to seconds)
                sleep_seconds = max(1.0, min(30.0, polling_interval / 1000.0))
                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                self.state = WorkerState.STOPPED
                break
            except Exception as e:
                consecutive_errors += 1
                if not self._first_poll_done:
                    logger.warning(
                        f"[CHAT POLLER]\n"
                        f"  FIRST_POLL\n"
                        f"  live_chat_id={self.live_chat_id}\n"
                        f"  status=FAILED\n"
                        f"  error={e}\n"
                        f"  retry_in={min(30.0, 3.0 * consecutive_errors)}s"
                    )
                else:
                    logger.warning(
                        f"Error polling chat for stream {self.stream_id} (error #{consecutive_errors}): {e}"
                    )
                if consecutive_errors >= 10:
                    self.state = WorkerState.FAILED
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

    async def _check_and_start_stream(self, channel_id: str, video_id: str, title: str | None = None) -> bool:
        """Resolve liveChatId, start ChatWorker, and send idempotent join greeting if needed."""
        is_misayu = channel_id == "UCCMwadkzXrznmMpZd5ek6PA"
        prefix = "[MISAYUISLIVE SCAN]" if is_misayu else f"[{channel_id} SCAN]"

        async with self._lock:
            if (
                channel_id in self._workers
                and self._workers[channel_id]._running
                and self._workers[channel_id].video_id == video_id
            ):
                return True

            # Resolve liveChatId
            live_chat_id = await self.youtube.get_live_chat_id(video_id)
            if not live_chat_id:
                logger.info(
                    f"[LIVE CHAT RESOLUTION] Video {video_id} has no active live chat. Not a live stream."
                )
                return False

            logger.info(
                f"{prefix} Status: LIVE\n"
                f"  Video ID: {video_id}\n"
                f"[LIVE CHAT RESOLUTION] Status: SUCCESS\n"
                f"  Live Chat ID: {live_chat_id}\n"
                f"[CHAT WORKER] Status: STARTING"
            )

            # Persist or update Stream in DB
            try:
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
                            join_message_sent=False,
                            started_at=datetime.now(UTC),
                            created_at=datetime.now(UTC),
                        )
                        session.add(stream)
                        await session.flush()
                        logger.info(f"[STREAM DB] Status: READY (Created new stream ID: {stream.id})")
                    else:
                        stream.live_chat_id = live_chat_id
                        stream.status = "LIVE"
                        if title and not stream.title:
                            stream.title = title
                        stream.updated_at = datetime.now(UTC)
                        logger.info(
                            f"[STREAM DB] Status: READY (Updated existing stream ID: {stream.id}, join_message_sent={stream.join_message_sent})"
                        )

                    stream_id = stream.id
                    should_send_join = not stream.join_message_sent

            except Exception as e:
                logger.error(
                    f"[STREAM DB] FAILED\n"
                    f"  operation=get_or_create_stream\n"
                    f"  channel_id={channel_id}\n"
                    f"  video_id={video_id}\n"
                    f"  error={e}",
                    exc_info=True,
                )
                return False

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

            # -------------------------------------------------------------------
            # Idempotent Join Greeting Message State Machine
            # -------------------------------------------------------------------
            logger.info(f"[JOIN MESSAGE]\n  status=CHECKING\n  already_sent={not should_send_join}")

            if should_send_join:
                if self.youtube.oauth.is_configured:
                    join_msg = settings.JOIN_MESSAGE
                    logger.info(f"[JOIN MESSAGE]\n  status=SENDING\n  live_chat_id={live_chat_id}")
                    try:
                        resp = await self.youtube.post_chat_message(live_chat_id, join_msg)
                        if resp:
                            async with get_session() as session:
                                s_stmt = select(Stream).where(Stream.id == stream_id)
                                s_res = await session.execute(s_stmt)
                                s_obj = s_res.scalar_one_or_none()
                                if s_obj:
                                    s_obj.join_message_sent = True

                                # Record as SYSTEM_JOIN_MESSAGE in audit_logs
                                audit = AuditLog(
                                    channel_id=channel_id,
                                    stream_id=stream_id,
                                    actor_user_id="SYSTEM",
                                    actor_username="Honney",
                                    command="SYSTEM_JOIN_MESSAGE",
                                    safe_arguments=join_msg,
                                    target_user_id=None,
                                    target_username=None,
                                    result="SUCCESS",
                                )
                                session.add(audit)
                            logger.info(f"[JOIN MESSAGE]\n  status=SENT\n  message='{join_msg}'")
                        else:
                            logger.warning(
                                "[JOIN MESSAGE]\n  status=FAILED\n  reason=post_chat_message returned None"
                            )
                    except Exception as e:
                        logger.error(f"[JOIN MESSAGE]\n  status=FAILED\n  error={e}", exc_info=True)
                else:
                    logger.warning("[JOIN MESSAGE]\n  status=SKIPPED\n  reason=OAuth not configured")
            else:
                logger.info(f"[JOIN MESSAGE]\n  status=SKIPPED\n  reason=already_sent for video {video_id}")

            return True

    async def scan_channel(self, channel_id: str) -> LiveDetectionResult:
        """Scan a single channel by its permanent UC ID for an active live broadcast."""
        is_misayu = channel_id == "UCCMwadkzXrznmMpZd5ek6PA"
        prefix = "[MISAYUISLIVE SCAN]" if is_misayu else f"[{channel_id} SCAN]"
        logger.info(f"{prefix}\n  Channel ID: {channel_id}\n  Status: CHECKING")

        result = await self.youtube.get_active_live_video(channel_id)

        if result.status == LiveDetectionStatus.LIVE:
            logger.info(f"{prefix}\n  Status: LIVE\n  Video ID: {result.video_id}")
            if result.video_id:
                await self._check_and_start_stream(channel_id, result.video_id, result.title)
            return result
        elif result.status == LiveDetectionStatus.OFFLINE:
            logger.info(f"{prefix}\n  Status: OFFLINE")
            return result
        elif result.status == LiveDetectionStatus.QUOTA_ERROR:
            logger.warning(
                f"{prefix}\n"
                f"  Status: QUOTA_ERROR\n"
                f"  Reason: {result.error_reason}\n"
                f"  Message: {result.error_message}\n"
                f"  Action: Retrying next cycle with backoff"
            )
            return result
        elif result.status == LiveDetectionStatus.NETWORK_ERROR:
            logger.warning(
                f"{prefix}\n"
                f"  Status: NETWORK_ERROR\n"
                f"  Message: {result.error_message}\n"
                f"  Action: Retrying next cycle with backoff"
            )
            return result
        else:
            logger.warning(
                f"{prefix}\n"
                f"  Status: API_ERROR (HTTP {result.http_status})\n"
                f"  Reason: {result.error_reason}\n"
                f"  Message: {result.error_message}\n"
                f"  Action: Retrying next cycle with backoff"
            )
            return result

    async def scan_all_channels_now(self) -> dict[str, LiveDetectionResult]:
        """Scan all enabled channels immediately (e.g. at startup or on manual trigger)."""
        channels = settings.load_channels()
        results: dict[str, LiveDetectionResult] = {}
        for ch in channels:
            try:
                res = await self.scan_channel(ch.channel_id)
                results[ch.channel_id] = res
            except Exception as e:
                logger.error(
                    f"Error during channel scan for {ch.channel_id} ({ch.name}): {e}",
                    extra={"channel_id": ch.channel_id, "operation": "scan_channel"},
                    exc_info=True,
                )
        return results

    async def connect_manual_stream(self, url_or_id: str) -> dict[str, Any]:
        """Manually connect bot to a YouTube Live stream by URL or video ID for testing."""
        video_id = parse_youtube_video_id(url_or_id)
        if not video_id:
            return {
                "success": False,
                "error": f"Invalid YouTube link or video ID: '{url_or_id}'. Please paste a valid YouTube URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)",
            }

        # Check if already connected
        for ch_id, w in list(self._workers.items()):
            if w._running and w.video_id == video_id:
                return {
                    "success": True,
                    "video_id": video_id,
                    "channel_id": ch_id,
                    "live_chat_id": w.live_chat_id,
                    "status": "ALREADY_CONNECTED",
                    "message": f"Bot is already connected to live stream {video_id}.",
                }

        # Fetch video metadata and activeLiveChatId
        video_info = await self.youtube.get_video_info(video_id)
        if not video_info:
            # Fallback to get_live_chat_id
            live_chat_id = await self.youtube.get_live_chat_id(video_id)
            if not live_chat_id:
                return {
                    "success": False,
                    "error": f"Could not find an active live chat for video '{video_id}'. Please ensure the stream is currently LIVE and live chat is enabled.",
                }
            channel_id = "MANUAL_TEST_CHANNEL"
            title = f"Live Stream ({video_id})"
            channel_title = "Manual Test Channel"
        else:
            live_chat_id = video_info.get("live_chat_id")
            channel_id = video_info.get("channel_id") or "MANUAL_TEST_CHANNEL"
            title = video_info.get("title") or f"Live Stream ({video_id})"
            channel_title = video_info.get("channel_title") or "YouTube Channel"

        if not live_chat_id:
            return {
                "success": False,
                "error": f"Video '{title}' ({video_id}) is not an active live stream or live chat is disabled.",
            }

        started = await self._check_and_start_stream(
            channel_id=channel_id,
            video_id=video_id,
            title=title,
        )
        if started:
            return {
                "success": True,
                "video_id": video_id,
                "title": title,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "live_chat_id": live_chat_id,
                "status": "CONNECTED",
                "message": f"Successfully connected bot to '{title}' ({video_id})!",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to start worker for live stream '{title}' ({video_id}).",
            }

    async def disconnect_stream(self, channel_id_or_video_id: str) -> dict[str, Any]:
        """Manually disconnect and stop a worker for a stream."""
        target_ch: str | None = None
        target_worker: ChatWorker | None = None

        async with self._lock:
            for ch_id, worker in list(self._workers.items()):
                if ch_id == channel_id_or_video_id or worker.video_id == channel_id_or_video_id:
                    target_ch = ch_id
                    target_worker = worker
                    break

            if target_worker and target_ch:
                await target_worker.stop()
                await target_worker._handle_stream_end()
                self._workers.pop(target_ch, None)
                return {
                    "success": True,
                    "message": f"Successfully disconnected worker for video {target_worker.video_id}.",
                }

        return {
            "success": False,
            "error": f"No active worker found for '{channel_id_or_video_id}'.",
        }

    def get_active_streams_status(self) -> list[dict[str, Any]]:
        """Return real-time diagnostic status of all currently active stream workers."""
        active = []
        for worker in list(self._workers.values()):
            active.append(
                {
                    "channel_id": worker.channel_id,
                    "video_id": worker.video_id,
                    "live_chat_id": worker.live_chat_id,
                    "stream_id": worker.stream_id,
                    "state": worker.state.value if hasattr(worker.state, "value") else str(worker.state),
                    "running": worker._running,
                    "first_poll_done": worker._first_poll_done,
                    "seen_messages_count": len(worker._seen_messages),
                    "recent_messages": worker._recent_chat_buffer[-20:],
                }
            )
        return active

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
                    await self.scan_channel(ch.channel_id)

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
