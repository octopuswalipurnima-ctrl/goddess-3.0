"""
Response Deduplication Service for AI Co-Host in GODDESS AI 2.0.

Prevents the AI Co-Host from sending repeated, near-identical replies.
"""

from collections import deque
import re
import time
from typing import Deque, Dict, Tuple

from app.core.logging import get_logger

logger = get_logger("cohost.deduplication")


class ResponseDeduplicator:
    """Tracks recent response texts per stream to avoid repetitive outputs."""

    def __init__(self, history_size: int = 10):
        self.history_size = history_size
        # stream_id -> deque of (normalized_text, timestamp)
        self._recent_responses: Dict[str, Deque[Tuple[str, float]]] = {}

    def _normalize(self, text: str) -> str:
        """Normalize text for repetition comparison."""
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()

    def is_duplicate(self, stream_id: str, text: str, max_age_seconds: float = 120.0) -> bool:
        """
        Check if normalized response matches any recent response in the stream window.
        """
        normalized = self._normalize(text)
        if not normalized or len(normalized) < 5:
            return False

        if stream_id not in self._recent_responses:
            self._recent_responses[stream_id] = deque(maxlen=self.history_size)

        now = time.time()
        for prev_text, ts in self._recent_responses[stream_id]:
            if prev_text == normalized and now - ts <= max_age_seconds:
                return True

        return False

    def record_response(self, stream_id: str, text: str) -> None:
        """Record response in stream history."""
        normalized = self._normalize(text)
        if normalized:
            if stream_id not in self._recent_responses:
                self._recent_responses[stream_id] = deque(maxlen=self.history_size)
            self._recent_responses[stream_id].append((normalized, time.time()))


# Global singleton response deduplicator
response_deduplicator = ResponseDeduplicator()
