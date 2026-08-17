"""
Response Deduplication and Similarity Engine for AI Co-Host in GODDESS AI 2.0.
Tracks bounded recent responses per stream (max 30) and detects exact duplicates & high lexical similarity.
"""

from collections import deque
import re
import time
from typing import Deque, Dict, Optional, Set, Tuple
from app.core.logging import get_logger

logger = get_logger("cohost.deduplication")


class ResponseDeduplicator:
    """Tracks bounded recent responses per stream (max 30) with Jaccard and exact similarity detection."""

    def __init__(self, history_size: int = 30):
        self.history_size = history_size
        # stream_id -> deque of (raw_text, normalized_text, token_set, timestamp)
        self._recent_responses: Dict[str, Deque[Tuple[str, str, Set[str], float]]] = {}

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison (lowercase, strip punctuation and extra spaces)."""
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()

    def _tokenize(self, text: str) -> Set[str]:
        """Extract word tokens from text."""
        normalized = self._normalize(text)
        return set(normalized.split())

    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Calculate Jaccard token overlap between two sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def is_duplicate(self, stream_id: str, text: str, max_age_seconds: float = 180.0) -> bool:
        """Check if normalized response exactly matches any recent response in the stream window."""
        normalized = self._normalize(text)
        if not normalized or len(normalized) < 4:
            return False

        if stream_id not in self._recent_responses:
            self._recent_responses[stream_id] = deque(maxlen=self.history_size)

        now = time.time()
        for _, prev_norm, _, ts in self._recent_responses[stream_id]:
            if prev_norm == normalized and (now - ts) <= max_age_seconds:
                return True
        return False

    def is_similar(
        self,
        stream_id: str,
        text: str,
        threshold: float = 0.65,
        max_age_seconds: float = 180.0,
    ) -> Tuple[bool, float]:
        """
        Check if candidate response has high lexical similarity to recent responses in this stream.
        Returns (is_similar, max_similarity_score).
        """
        tokens = self._tokenize(text)
        if not tokens or len(tokens) < 3:
            return self.is_duplicate(stream_id, text, max_age_seconds), 1.0 if self.is_duplicate(stream_id, text) else 0.0

        if stream_id not in self._recent_responses:
            self._recent_responses[stream_id] = deque(maxlen=self.history_size)
            return False, 0.0

        now = time.time()
        max_sim = 0.0

        for _, prev_norm, prev_tokens, ts in self._recent_responses[stream_id]:
            if (now - ts) <= max_age_seconds:
                # 1. Exact match check
                if prev_norm == self._normalize(text):
                    return True, 1.0
                # 2. Jaccard similarity check
                sim = self._jaccard_similarity(tokens, prev_tokens)
                if sim > max_sim:
                    max_sim = sim
                if sim >= threshold:
                    return True, sim

        return False, max_sim

    def record_response(self, stream_id: str, text: str) -> None:
        """Record response in stream-isolated bounded history."""
        normalized = self._normalize(text)
        if normalized:
            tokens = self._tokenize(text)
            if stream_id not in self._recent_responses:
                self._recent_responses[stream_id] = deque(maxlen=self.history_size)
            self._recent_responses[stream_id].append((text, normalized, tokens, time.time()))

    def clear_stream_history(self, stream_id: str) -> None:
        """Clear response history for a specific stream."""
        if stream_id in self._recent_responses:
            del self._recent_responses[stream_id]
            logger.info(f"Cleared response history for stream '{stream_id}'.")


# Global singleton response deduplicator
response_deduplicator = ResponseDeduplicator()
