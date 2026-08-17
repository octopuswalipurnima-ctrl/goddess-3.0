"""
Action Idempotency and Duplicate Mutation Guard for GODDESS AI 2.0.

Guarantees that duplicate action IDs or re-delivered events across moderation,
co-host replies, commands, and emergency controls NEVER produce duplicate mutations.
Uses bounded sliding in-memory caches with optional Redis backing.
"""

from collections import deque
from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional, Tuple
from app.core.logging import get_logger
from app.core.redis import redis_state

logger = get_logger("core.idempotency")

MAX_IN_MEMORY_IDEMPOTENCY_KEYS = 5000
DEFAULT_IDEMPOTENCY_TTL_SECONDS = 300


class ActionIdempotencyManager:
    """Bounded, stream-isolated idempotency guard."""

    def __init__(self, max_keys: int = MAX_IN_MEMORY_IDEMPOTENCY_KEYS):
        self._max_keys = max_keys
        # action_key -> (timestamp, result_payload)
        self._local_cache: Dict[str, Tuple[float, Optional[Dict[str, Any]]]] = {}
        self._key_order: deque = deque(maxlen=max_keys)

    def _build_key(self, action_key: str, stream_id: Optional[str] = None) -> str:
        s_part = stream_id or "GLOBAL"
        return f"idemp:{s_part}:{action_key}"

    async def is_duplicate(self, action_key: str, stream_id: Optional[str] = None) -> bool:
        """
        Check if the action key has already been registered and is within its valid TTL.
        """
        full_key = self._build_key(action_key, stream_id)
        now = time.time()

        # Check local cache first
        if full_key in self._local_cache:
            ts, _ = self._local_cache[full_key]
            if now - ts < DEFAULT_IDEMPOTENCY_TTL_SECONDS:
                return True
            else:
                self._local_cache.pop(full_key, None)

        # Check Redis if active
        if redis_state.is_connected:
            try:
                val = await redis_state.get(full_key)
                if val is not None:
                    return True
            except Exception:
                pass

        return False

    async def register_action(
        self,
        action_key: str,
        stream_id: Optional[str] = None,
        result_payload: Optional[Dict[str, Any]] = None,
        ttl: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS,
    ) -> bool:
        """
        Register action execution. Returns True if successfully registered (first execution),
        or False if already registered (duplicate execution).
        """
        if await self.is_duplicate(action_key, stream_id):
            return False

        full_key = self._build_key(action_key, stream_id)
        now = time.time()

        # Enforce memory bounds
        if len(self._local_cache) >= self._max_keys:
            oldest = self._key_order.popleft() if self._key_order else None
            if oldest:
                self._local_cache.pop(oldest, None)

        self._local_cache[full_key] = (now, result_payload)
        self._key_order.append(full_key)

        # Mirror to Redis if active
        if redis_state.is_connected:
            try:
                await redis_state.set(full_key, "REGISTERED", ttl=ttl)
            except Exception:
                pass

        return True

    async def get_cached_result(
        self, action_key: str, stream_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve stored execution result for a duplicate action."""
        full_key = self._build_key(action_key, stream_id)
        if full_key in self._local_cache:
            ts, payload = self._local_cache[full_key]
            if time.time() - ts < DEFAULT_IDEMPOTENCY_TTL_SECONDS:
                return payload
        return None

    def clear(self) -> None:
        """Clear local in-memory cache (used for test isolation)."""
        self._local_cache.clear()
        self._key_order.clear()


# Global singleton
idempotency_manager = ActionIdempotencyManager()
