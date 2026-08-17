"""
Cooldown and Rate-Limiting Tracker for AI Co-Host in GODDESS AI 2.0.

Enforces multi-stream isolated global cooldowns (5s), per-user cooldowns (30s),
per-minute stream response caps (12/min), and per-user window caps (3/window).
"""

from collections import deque
import time
from typing import Deque, Dict, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger("cohost.cooldowns")


class StreamCooldownState:
    """Isolated rate-limiting state for a single stream session."""

    def __init__(self):
        self.last_global_response_time: float = 0.0
        # author_id -> last response timestamp
        self.user_last_response_time: Dict[str, float] = {}
        # deque of timestamps in last 60s
        self.stream_response_timestamps: Deque[float] = deque()
        # author_id -> deque of timestamps in last 60s
        self.user_response_timestamps: Dict[str, Deque[float]] = {}

    def cleanup_old_records(self, now: float, cutoff_seconds: float = 60.0) -> None:
        """Purge sliding rate tracking records older than cutoff."""
        while self.stream_response_timestamps and now - self.stream_response_timestamps[0] > cutoff_seconds:
            self.stream_response_timestamps.popleft()

        for author_id in list(self.user_response_timestamps.keys()):
            q = self.user_response_timestamps[author_id]
            while q and now - q[0] > cutoff_seconds:
                q.popleft()
            if not q:
                del self.user_response_timestamps[author_id]


class CoHostCooldownTracker:
    """Multi-stream partitioned cooldown and rate limiter."""

    def __init__(self):
        self._streams: Dict[str, StreamCooldownState] = {}

    def _get_stream_state(self, stream_id: str) -> StreamCooldownState:
        if stream_id not in self._streams:
            self._streams[stream_id] = StreamCooldownState()
        return self._streams[stream_id]

    def check_cooldowns(
        self,
        stream_id: str,
        author_id: str,
        global_cooldown: float = 5.0,
        user_cooldown: float = 30.0,
        max_per_minute: int = 12,
        max_per_user: int = 3,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if sending a response is allowed under cooldowns and rate limits.
        Returns (is_allowed, block_reason).
        """
        now = time.time()
        state = self._get_stream_state(stream_id)
        state.cleanup_old_records(now)

        # 1. Global stream cooldown (e.g. 5 seconds)
        if now - state.last_global_response_time < global_cooldown:
            remaining = global_cooldown - (now - state.last_global_response_time)
            return False, f"Global response cooldown active ({remaining:.1f}s remaining)"

        # 2. Per-user cooldown (e.g. 30 seconds)
        if author_id in state.user_last_response_time:
            last_time = state.user_last_response_time[author_id]
            if now - last_time < user_cooldown:
                remaining = user_cooldown - (now - last_time)
                return False, f"Per-user response cooldown active ({remaining:.1f}s remaining)"

        # 3. Stream per-minute cap (e.g. max 12 responses/min)
        if len(state.stream_response_timestamps) >= max_per_minute:
            return False, f"Stream response rate limit reached ({len(state.stream_response_timestamps)}/{max_per_minute} per min)"

        # 4. User per-window cap (e.g. max 3 responses/window)
        if author_id in state.user_response_timestamps:
            if len(state.user_response_timestamps[author_id]) >= max_per_user:
                return False, f"User response limit reached ({len(state.user_response_timestamps[author_id])}/{max_per_user} per min)"

        return True, None

    def record_response(self, stream_id: str, author_id: str) -> None:
        """Record that a response was approved/sent to update cooldown timers."""
        now = time.time()
        state = self._get_stream_state(stream_id)
        state.last_global_response_time = now
        state.user_last_response_time[author_id] = now
        state.stream_response_timestamps.append(now)

        if author_id not in state.user_response_timestamps:
            state.user_response_timestamps[author_id] = deque()
        state.user_response_timestamps[author_id].append(now)


# Global singleton cooldown tracker
cohost_cooldown_tracker = CoHostCooldownTracker()
