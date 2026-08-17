"""
Stream Stats Module for GODDESS AI 2.0.

Tracks live per-stream telemetry (messages processed, moderation actions,
Co-Host replies, uptime, and throughput rates) with multi-stream isolation.
"""

from collections import deque
import time
from typing import Any, Deque, Dict

from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.models import ModuleCapability, ModuleMetadata

logger = get_logger("modules.stream_stats")


class StreamStatsState:
    """Telemetry counters and sliding rate trackers for a single stream."""

    def __init__(self):
        self.start_time: float = time.time()
        self.messages_count: int = 0
        self.moderation_actions_count: int = 0
        self.cohost_responses_count: int = 0
        self.module_events_count: int = 0
        # sliding deque of message timestamps in last 60s
        self.recent_message_timestamps: Deque[float] = deque()

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def messages_per_minute(self) -> float:
        now = time.time()
        while self.recent_message_timestamps and now - self.recent_message_timestamps[0] > 60.0:
            self.recent_message_timestamps.popleft()
        return float(len(self.recent_message_timestamps))


class StreamStatsModule(BaseModule):
    """Monitors live stream telemetry and event throughput."""

    def __init__(self):
        metadata = ModuleMetadata(
            id="stream_stats",
            name="Stream Live Stats",
            version="1.0.0",
            description="Aggregates live stream metrics (message rate, moderation decisions, co-host replies, uptime).",
            category="stats",
            capabilities=[
                ModuleCapability.STREAM_READ,
                ModuleCapability.CHAT_READ,
                ModuleCapability.MODERATION_READ,
                ModuleCapability.COHOST_READ,
            ],
            supported_events=[
                "CHAT_MESSAGE",
                "MODERATION_ACTION_EXECUTED",
                "COHOST_RESPONSE_SENT",
                "STREAM_STARTED",
                "STREAM_ENDED",
            ],
        )
        super().__init__(metadata)
        # stream_id -> StreamStatsState
        self._stats: Dict[str, StreamStatsState] = {}

    def _get_stats(self, stream_id: str) -> StreamStatsState:
        if stream_id not in self._stats:
            self._stats[stream_id] = StreamStatsState()
        return self._stats[stream_id]

    def get_stream_metrics(self, stream_id: str) -> Dict[str, Any]:
        """Export computed metrics for a stream."""
        state = self._get_stats(stream_id)
        return {
            "stream_id": stream_id,
            "uptime_seconds": round(state.uptime_seconds, 1),
            "messages_count": state.messages_count,
            "messages_per_minute": state.messages_per_minute,
            "moderation_actions_count": state.moderation_actions_count,
            "cohost_responses_count": state.cohost_responses_count,
            "module_events_count": state.module_events_count,
        }

    async def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Process incoming events to update stream telemetry."""
        stream_id = event_data.get("stream_id")
        if not stream_id:
            return

        state = self._get_stats(stream_id)
        state.module_events_count += 1
        now = time.time()

        if event_name == "CHAT_MESSAGE":
            state.messages_count += 1
            state.recent_message_timestamps.append(now)
        elif event_name == "MODERATION_ACTION_EXECUTED":
            state.moderation_actions_count += 1
        elif event_name == "COHOST_RESPONSE_SENT":
            state.cohost_responses_count += 1
        elif event_name == "STREAM_STARTED":
            state.start_time = now
        elif event_name == "STREAM_ENDED":
            pass
