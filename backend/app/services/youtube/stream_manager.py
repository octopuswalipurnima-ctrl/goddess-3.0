"""
Central Stream Manager for GODDESS AI 2.0.

Orchestrates multiple concurrent StreamSession instances (supports up to 4 simultaneous streams),
enforces capacity limits, prevents duplicate sessions, and provides centralized lifecycle control.
"""

import asyncio
from typing import Dict, List, Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.exceptions import (
    DuplicateStreamError,
    MaxStreamsReachedError,
    StreamNotFoundError,
)
from app.services.youtube.models import StreamSessionSummary, StreamStatus
from app.services.youtube.stream_session import StreamSession

logger = get_logger("youtube.manager")


class StreamManager:
    """Central manager for YouTube live stream sessions."""

    def __init__(
        self,
        max_concurrent_streams: int = 4,
        api_client: Optional[YouTubeAPIClient] = None,
    ):
        self.max_concurrent_streams = max_concurrent_streams
        self.client = api_client or youtube_client
        self._sessions: Dict[str, StreamSession] = {}
        self._lock = asyncio.Lock()

        # Subscribe to STREAM_ENDED for automated session cleanup
        event_bus.subscribe("STREAM_ENDED", self._handle_stream_ended)

    @property
    def active_stream_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_active)

    @property
    def total_stream_count(self) -> int:
        return len(self._sessions)

    async def create_session(
        self,
        stream_id: str,
        channel_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> StreamSession:
        """
        Create and optionally start a new isolated StreamSession.
        Enforces maximum concurrent capacity (default: 4) and prevents duplicate sessions.
        """
        async with self._lock:
            cleaned_id = stream_id.strip()

            # 1. Duplicate Stream Protection
            if cleaned_id in self._sessions:
                existing = self._sessions[cleaned_id]
                if existing.is_active:
                    logger.warning(f"Attempted to create duplicate session for active stream '{cleaned_id}'.")
                    raise DuplicateStreamError(f"StreamSession for stream '{cleaned_id}' already exists and is active.")
                else:
                    # Remove stale/ended session before re-creating
                    del self._sessions[cleaned_id]

            # 2. Concurrency Limit Check
            if self.active_stream_count >= self.max_concurrent_streams:
                logger.error(
                    f"Max concurrent stream capacity ({self.max_concurrent_streams}) reached. Cannot add '{cleaned_id}'."
                )
                raise MaxStreamsReachedError(
                    f"Maximum concurrent live streams limit ({self.max_concurrent_streams}) reached."
                )

            # 3. Initialize Session
            session = StreamSession(
                stream_id=cleaned_id,
                channel_id=channel_id,
                api_client=self.client,
            )
            self._sessions[cleaned_id] = session
            logger.info(f"Registered new StreamSession '{cleaned_id}' ({self.active_stream_count}/{self.max_concurrent_streams} active)")

        await event_bus.publish(
            "STREAM_STARTED",
            {
                "stream_id": cleaned_id,
                "channel_id": channel_id,
            },
        )

        if auto_start:
            try:
                await session.start()
            except Exception as e:
                logger.error(f"Failed to auto-start session '{cleaned_id}': {e}")
                # Session is marked FAILED inside start()

        return session

    def get_session(self, stream_id: str) -> Optional[StreamSession]:
        """Retrieve an existing StreamSession by stream_id."""
        return self._sessions.get(stream_id.strip())

    def list_sessions(self) -> List[StreamSessionSummary]:
        """Return summaries of all currently tracked sessions."""
        return [session.to_summary() for session in self._sessions.values()]

    async def stop_session(self, stream_id: str, reason: str = "Manual stop") -> bool:
        """Stop a specific stream session by ID."""
        cleaned_id = stream_id.strip()
        session = self.get_session(cleaned_id)
        if not session:
            logger.warning(f"Cannot stop non-existent session '{cleaned_id}'.")
            return False

        await session.stop(reason=reason)
        async with self._lock:
            if cleaned_id in self._sessions:
                del self._sessions[cleaned_id]

        logger.info(f"StreamSession '{cleaned_id}' stopped and removed.")
        return True

    async def stop_all(self, reason: str = "System shutdown") -> None:
        """Stop all currently active stream sessions."""
        sessions_to_stop = list(self._sessions.values())
        if not sessions_to_stop:
            return

        logger.info(f"Stopping all {len(sessions_to_stop)} active stream sessions...")
        tasks = [session.stop(reason=reason) for session in sessions_to_stop]
        await asyncio.gather(*tasks, return_exceptions=True)

        async with self._lock:
            self._sessions.clear()

    async def _handle_stream_ended(self, payload: dict) -> None:
        """Automated event handler triggered when a stream ends."""
        stream_id = payload.get("stream_id")
        if stream_id and stream_id in self._sessions:
            logger.info(f"StreamManager received STREAM_ENDED for '{stream_id}'. Cleaning up...")
            async with self._lock:
                if stream_id in self._sessions:
                    del self._sessions[stream_id]


# Global singleton instance of StreamManager
stream_manager = StreamManager()
