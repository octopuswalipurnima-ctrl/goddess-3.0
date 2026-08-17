"""
Production Stream Supervisor for GODDESS AI 2.0.

Provides autonomous lifecycle management, automatic attach/reconnect, termination detection,
and state supervision for up to 4 simultaneous YouTube Live streams with strict isolation.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.provider_errors import classify_provider_error
from app.core.safety_controller import safety_controller
from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.exceptions import (
    DuplicateStreamError,
    MaxStreamsReachedError,
    StreamNotFoundError,
)
from app.services.youtube.models import StreamStatus
from app.services.youtube.stream_session import StreamSession

logger = get_logger("youtube.supervisor")


class SupervisorState(str, Enum):
    DISCOVERING = "DISCOVERING"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    RECONNECTING = "RECONNECTING"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"
    STOPPING = "STOPPING"
    ENDED = "ENDED"
    FAILED = "FAILED"


class StreamSupervisorSummary(BaseModel):
    stream_id: str
    video_id: str
    channel_id: Optional[str] = None
    title: Optional[str] = None
    state: SupervisorState
    live_chat_id: Optional[str] = None
    concurrent_viewers: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    reconnect_attempts: int = 0
    uptime_seconds: float = 0.0
    attached_at: Optional[str] = None
    last_message_at: Optional[str] = None
    last_reconnect_at: Optional[str] = None
    last_error: Optional[str] = None
    safe_mode: bool = False
    emergency_stop: bool = False


class StreamSupervisorSession:
    """Encapsulates supervised lifecycle state and tasks for a single stream."""

    def __init__(
        self,
        stream_id: str,
        channel_id: Optional[str] = None,
        api_client: Optional[YouTubeAPIClient] = None,
        auto_reconnect: bool = True,
    ):
        self.stream_id = stream_id
        self.video_id = stream_id
        self.channel_id = channel_id
        self.client = api_client or youtube_client
        self.state = SupervisorState.CONNECTING
        self.auto_reconnect = auto_reconnect

        self.session: Optional[StreamSession] = None
        self.created_at = time.time()
        self.attached_at: Optional[float] = None
        self.last_heartbeat_at = self.created_at
        self.reconnect_attempts = 0
        self.last_error: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.state in (
            SupervisorState.CONNECTING,
            SupervisorState.LIVE,
            SupervisorState.RECONNECTING,
            SupervisorState.DEGRADED,
            SupervisorState.SAFE_MODE,
        )

    @property
    def uptime_seconds(self) -> float:
        if self.attached_at and self.is_active:
            return round(time.time() - self.attached_at, 1)
        return 0.0

    async def start(self) -> None:
        """Initialize StreamSession and connect to live stream."""
        self.state = SupervisorState.CONNECTING
        now = time.time()
        self.attached_at = now
        self.last_heartbeat_at = now

        try:
            self.session = StreamSession(
                stream_id=self.stream_id,
                channel_id=self.channel_id,
                api_client=self.client,
            )
            await self.session.start()

            if safety_controller.is_stream_safe_mode(self.stream_id):
                self.state = SupervisorState.SAFE_MODE
            else:
                self.state = SupervisorState.LIVE

            self.last_error = None
            logger.info(f"StreamSupervisor '{self.stream_id}' successfully attached: LIVE")

            await event_bus.publish(
                "STREAM_SUPERVISOR_EVENT",
                {
                    "stream_id": self.stream_id,
                    "state": self.state.value,
                    "event": "ATTACHED_LIVE",
                },
            )

        except Exception as exc:
            code, sanitized_msg, _ = classify_provider_error(exc)
            self.state = SupervisorState.FAILED
            self.last_error = sanitized_msg
            logger.error(f"StreamSupervisor '{self.stream_id}' failed to start ({code.value}): {sanitized_msg}")
            raise

    async def reconnect(self) -> bool:
        """Perform a controlled reconnection attempt with safety gates."""
        allowed, reason = safety_controller.can_reconnect(self.stream_id, self.reconnect_attempts)
        if not allowed:
            logger.warning(f"Reconnection blocked for '{self.stream_id}': {reason}")
            self.state = SupervisorState.FAILED
            return False

        self.reconnect_attempts += 1
        self.state = SupervisorState.RECONNECTING
        logger.info(f"Reconnecting stream '{self.stream_id}' (Attempt {self.reconnect_attempts})...")

        try:
            if self.session:
                await self.session.stop(reason="Reconnecting")

            self.session = StreamSession(
                stream_id=self.stream_id,
                channel_id=self.channel_id,
                api_client=self.client,
            )
            await self.session.start()

            self.state = (
                SupervisorState.SAFE_MODE
                if safety_controller.is_stream_safe_mode(self.stream_id)
                else SupervisorState.LIVE
            )
            self.last_error = None
            logger.info(f"Stream '{self.stream_id}' successfully reconnected: LIVE")
            return True

        except Exception as exc:
            code, sanitized_msg, _ = classify_provider_error(exc)
            self.state = SupervisorState.DEGRADED if self.reconnect_attempts < 5 else SupervisorState.FAILED
            self.last_error = sanitized_msg
            logger.warning(f"Reconnection failed for '{self.stream_id}': {sanitized_msg}")
            return False

    async def stop(self, reason: str = "Manual stop") -> None:
        """Gracefully disconnect and tear down live stream session."""
        self.state = SupervisorState.STOPPING
        logger.info(f"Stopping supervised stream '{self.stream_id}' (Reason: {reason})")

        if self.session:
            try:
                await self.session.stop(reason=reason)
            except Exception as exc:
                logger.warning(f"Error while stopping session '{self.stream_id}': {exc}")
            self.session = None

        self.state = SupervisorState.ENDED
        await event_bus.publish(
            "STREAM_SUPERVISOR_EVENT",
            {
                "stream_id": self.stream_id,
                "state": SupervisorState.ENDED.value,
                "reason": reason,
                "uptime_seconds": self.uptime_seconds,
            },
        )

    def to_summary(self) -> StreamSupervisorSummary:
        """Export safe telemetry summary."""
        attached_at_str = (
            datetime.fromtimestamp(self.attached_at, timezone.utc).isoformat()
            if self.attached_at
            else None
        )
        sess_summary = self.session.to_summary() if self.session else None

        return StreamSupervisorSummary(
            stream_id=self.stream_id,
            video_id=self.video_id,
            channel_id=self.channel_id or (sess_summary.channel_id if sess_summary else None),
            title=sess_summary.title if sess_summary else None,
            state=self.state,
            live_chat_id=sess_summary.live_chat_id if sess_summary else None,
            concurrent_viewers=sess_summary.concurrent_viewers if sess_summary else 0,
            messages_received=sess_summary.messages_received if sess_summary else 0,
            messages_sent=sess_summary.messages_sent if sess_summary else 0,
            reconnect_attempts=self.reconnect_attempts,
            uptime_seconds=self.uptime_seconds,
            attached_at=attached_at_str,
            last_message_at=sess_summary.last_message_at if sess_summary else None,
            last_reconnect_at=sess_summary.last_reconnect_at if sess_summary else None,
            last_error=self.last_error,
            safe_mode=safety_controller.is_stream_safe_mode(self.stream_id),
            emergency_stop=safety_controller.is_stream_emergency(self.stream_id),
        )


class StreamSupervisor:
    """Production Stream Supervisor managing up to 4 simultaneous YouTube streams."""

    def __init__(
        self,
        max_concurrent_streams: int = 4,
        api_client: Optional[YouTubeAPIClient] = None,
    ):
        self.max_concurrent_streams = max_concurrent_streams
        self.client = api_client or youtube_client
        # stream_id -> StreamSupervisorSession
        self._supervisors: Dict[str, StreamSupervisorSession] = {}
        self._lock = asyncio.Lock()

        # Subscribe to EventBus lifecycle events
        event_bus.subscribe("STREAM_ENDED", self._on_stream_ended)
        event_bus.subscribe("YOUTUBE_ERROR", self._on_youtube_error)

    @property
    def active_stream_count(self) -> int:
        return sum(1 for s in self._supervisors.values() if s.is_active)

    @property
    def total_stream_count(self) -> int:
        return len(self._supervisors)

    async def attach_stream(
        self,
        stream_id: str,
        channel_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> StreamSupervisorSession:
        """
        Attach and start supervising a YouTube live stream.
        Enforces maximum 4 concurrent stream capacity and prevents duplicate streams.
        """
        cleaned_id = stream_id.strip()
        async with self._lock:
            # 1. Duplicate check
            if cleaned_id in self._supervisors:
                existing = self._supervisors[cleaned_id]
                if existing.is_active:
                    raise DuplicateStreamError(f"Stream '{cleaned_id}' is already actively supervised.")
                else:
                    # Clean up ended/failed supervisor before re-creating
                    del self._supervisors[cleaned_id]

            # 2. Concurrency limit check
            if self.active_stream_count >= self.max_concurrent_streams:
                raise MaxStreamsReachedError(
                    f"Maximum concurrent streams limit ({self.max_concurrent_streams}) reached. Cannot attach '{cleaned_id}'."
                )

            # 3. Create supervisor session
            sup_session = StreamSupervisorSession(
                stream_id=cleaned_id,
                channel_id=channel_id,
                api_client=self.client,
            )
            self._supervisors[cleaned_id] = sup_session

        if auto_start:
            await sup_session.start()

        return sup_session

    async def detach_stream(self, stream_id: str, reason: str = "Manual detach") -> bool:
        """Stop and detach an active supervised stream session."""
        async with self._lock:
            if stream_id not in self._supervisors:
                return False
            sup_session = self._supervisors[stream_id]

        await sup_session.stop(reason=reason)
        return True

    async def reconnect_stream(self, stream_id: str) -> bool:
        """Explicitly trigger reconnection for a stream."""
        if stream_id not in self._supervisors:
            return False
        return await self._supervisors[stream_id].reconnect()

    def get_supervisor_session(self, stream_id: str) -> Optional[StreamSupervisorSession]:
        """Fetch supervisor session for stream_id."""
        return self._supervisors.get(stream_id)

    def list_supervisor_sessions(self) -> List[StreamSupervisorSummary]:
        """List safe telemetry summaries for all supervised streams."""
        return [s.to_summary() for s in self._supervisors.values()]

    async def _on_stream_ended(self, data: Dict[str, Any]) -> None:
        """Handle stream termination event by finalizing supervisor session."""
        stream_id = data.get("stream_id")
        if stream_id and stream_id in self._supervisors:
            sup = self._supervisors[stream_id]
            if sup.is_active:
                logger.info(f"StreamSupervisor detected stream '{stream_id}' ended. Cleaning up.")
                await sup.stop(reason=data.get("reason", "Stream ended"))

    async def _on_youtube_error(self, data: Dict[str, Any]) -> None:
        """Handle YouTube error by placing affected stream into DEGRADED or RECONNECTING."""
        stream_id = data.get("stream_id")
        if stream_id and stream_id in self._supervisors:
            sup = self._supervisors[stream_id]
            if sup.is_active and sup.state == SupervisorState.LIVE:
                sup.state = SupervisorState.DEGRADED
                sup.last_error = data.get("error", "YouTube provider error")
                logger.warning(f"Stream '{stream_id}' supervisor state transitioned to DEGRADED: {sup.last_error}")

    async def shutdown(self) -> None:
        """Gracefully stop all active stream supervisors on application shutdown."""
        logger.info(f"Shutting down StreamSupervisor with {self.active_stream_count} active stream(s)...")
        tasks = [sup.stop(reason="Application shutdown") for sup in self._supervisors.values() if sup.is_active]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._supervisors.clear()
        logger.info("StreamSupervisor shutdown complete.")


# Global singleton instance
stream_supervisor = StreamSupervisor()
