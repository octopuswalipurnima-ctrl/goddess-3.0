"""
Transient Redis State Management and Distributed Safety for GODDESS AI 2.0.

Provides distributed cooldowns, rate limits, short-lived locks, and idempotency caching
with automatic fail-safe fallback to local in-memory storage when Redis is unconfigured or unavailable.
Never stores permanent audit logs or raw secrets in Redis.
"""

import asyncio
from contextlib import asynccontextmanager
import time
from typing import Any, AsyncGenerator, Dict, Optional
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("core.redis")


class InMemoryFallbackState:
    """Thread-safe and async-safe in-memory store for transient state with TTL eviction."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expirations: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _cleanup_expired(self, now: float) -> None:
        expired_keys = [k for k, exp in self._expirations.items() if now >= exp]
        for k in expired_keys:
            self._store.pop(k, None)
            self._expirations.pop(k, None)

    async def set(self, key: str, value: Any, ex: Optional[float] = None) -> bool:
        async with self._lock:
            now = time.time()
            self._cleanup_expired(now)
            self._store[key] = value
            if ex is not None and ex > 0:
                self._expirations[key] = now + ex
            else:
                self._expirations.pop(key, None)
            return True

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            now = time.time()
            self._cleanup_expired(now)
            return self._store.get(key)

    async def set_if_not_exists(self, key: str, value: Any, ex: Optional[float] = None) -> bool:
        async with self._lock:
            now = time.time()
            self._cleanup_expired(now)
            if key in self._store:
                return False
            self._store[key] = value
            if ex is not None and ex > 0:
                self._expirations[key] = now + ex
            return True

    async def increment(self, key: str, ex: Optional[int] = None) -> int:
        async with self._lock:
            now = time.time()
            self._cleanup_expired(now)
            val = self._store.get(key, 0)
            if not isinstance(val, int):
                val = 0
            val += 1
            self._store[key] = val
            if ex is not None and key not in self._expirations:
                self._expirations[key] = now + ex
            return val

    async def delete(self, key: str) -> bool:
        async with self._lock:
            removed = self._store.pop(key, None) is not None
            self._expirations.pop(key, None)
            return removed


class RedisStateManager:
    """Centralized manager for transient distributed state with automatic fail-safe fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[aioredis.Redis] = None
        self._fallback = InMemoryFallbackState()
        self._is_connected = False

    async def initialize(self) -> None:
        """Initialize Redis connection if REDIS_URL is configured."""
        if not self.redis_url:
            logger.info("REDIS_URL not configured. Operating in safe local in-memory mode.")
            return

        try:
            self._client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            await self._client.ping()
            self._is_connected = True
            logger.info("Connected to Redis distributed state store.")
        except Exception as exc:
            logger.warning(f"Failed to connect to Redis ({exc}). Falling back to safe in-memory store.")
            self._is_connected = False

    async def close(self) -> None:
        """Gracefully close Redis connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._is_connected = False
            logger.info("Redis connection closed.")

    # --- Distributed Cooldowns ---

    async def set_cooldown(self, key: str, ttl_seconds: float) -> bool:
        """Set a cooldown key that automatically expires after ttl_seconds."""
        if self._is_connected and self._client:
            try:
                await self._client.set(f"cooldown:{key}", "1", px=int(ttl_seconds * 1000))
                return True
            except Exception as err:
                logger.warning(f"Redis set_cooldown error: {err}. Using in-memory fallback.")
                self._is_connected = False

        return await self._fallback.set(f"cooldown:{key}", "1", ex=ttl_seconds)

    async def is_on_cooldown(self, key: str) -> bool:
        """Check if a cooldown key is currently active."""
        if self._is_connected and self._client:
            try:
                val = await self._client.get(f"cooldown:{key}")
                return val is not None
            except Exception as err:
                logger.warning(f"Redis is_on_cooldown error: {err}. Using in-memory fallback.")
                self._is_connected = False

        val = await self._fallback.get(f"cooldown:{key}")
        return val is not None

    # --- Idempotency Locks ---

    async def check_and_set_idempotency(self, key: str, ttl_seconds: float = 300.0) -> bool:
        """
        Atomically check and record an idempotency key.
        Returns True if this is the FIRST time the key is seen (lock acquired).
        Returns False if the key has ALREADY been registered (duplicate action).
        """
        full_key = f"idempotency:{key}"
        if self._is_connected and self._client:
            try:
                # set nx=True returns True if set, None/False if already exists
                acquired = await self._client.set(full_key, "1", nx=True, px=int(ttl_seconds * 1000))
                return bool(acquired)
            except Exception as err:
                logger.warning(f"Redis check_and_set_idempotency error: {err}. Using in-memory fallback.")
                self._is_connected = False

        # Fallback to in-memory atomic set
        return await self._fallback.set_if_not_exists(full_key, "1", ex=ttl_seconds)

    # --- Distributed Counter / Rate Limiting ---

    async def increment_counter(self, key: str, ttl_seconds: int = 60) -> int:
        """Increment a rate-limit counter with TTL."""
        full_key = f"rate:{key}"
        if self._is_connected and self._client:
            try:
                pipe = self._client.pipeline()
                pipe.incr(full_key)
                pipe.expire(full_key, ttl_seconds)
                results = await pipe.execute()
                return int(results[0])
            except Exception as err:
                logger.warning(f"Redis increment_counter error: {err}. Using in-memory fallback.")
                self._is_connected = False

        return await self._fallback.increment(full_key, ex=ttl_seconds)

    # --- Diagnostics & Health ---

    async def ping(self) -> Dict[str, Any]:
        """Check Redis connectivity, latency, and operational mode."""
        if not self.redis_url:
            return {
                "status": "NOT_CONFIGURED",
                "details": "REDIS_URL is not set in environment (using safe in-memory fallback)",
                "mode": "IN_MEMORY",
                "latency_ms": None,
            }

        start = time.perf_counter()
        try:
            if not self._client:
                await self.initialize()

            if self._client:
                await self._client.ping()
                self._is_connected = True
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "status": "HEALTHY",
                    "details": "Redis connection active",
                    "mode": "DISTRIBUTED",
                    "latency_ms": latency_ms,
                }
        except Exception as exc:
            self._is_connected = False
            return {
                "status": "UNAVAILABLE",
                "details": f"Redis connection failed: {type(exc).__name__} (safe in-memory fallback active)",
                "mode": "FALLBACK_IN_MEMORY",
                "latency_ms": None,
            }

        return {
            "status": "DEGRADED",
            "details": "Redis disconnected (using in-memory fallback)",
            "mode": "FALLBACK_IN_MEMORY",
            "latency_ms": None,
        }


# Global singleton Redis State Manager
redis_state = RedisStateManager()
