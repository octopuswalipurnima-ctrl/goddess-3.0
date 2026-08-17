"""
Centralized Credential & Quota Manager for Google Gemini API.

Manages up to 4 rotated Gemini API keys, tracks per-key health states, enforces cooldowns,
and publishes credential lifecycle events to the Event Bus.
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.gemini.exceptions import CredentialUnavailableError
from app.services.gemini.models import CredentialHealth, CredentialState

logger = get_logger("gemini.credentials")


class GeminiCredentialSlot:
    """Internal representation of a Gemini API credential slot."""

    def __init__(self, key_id: str, raw_key: str):
        self.key_id = key_id
        self.raw_key = raw_key
        self.state = CredentialState.AVAILABLE if raw_key and raw_key.strip() else CredentialState.UNCONFIGURED
        self.failure_count = 0
        self.total_requests = 0
        self.last_used_timestamp: Optional[float] = None
        self.cooldown_until_timestamp: Optional[float] = None
        self.last_error: Optional[str] = None

    def is_usable(self, now: float) -> bool:
        if self.state == CredentialState.DISABLED or self.state == CredentialState.UNCONFIGURED:
            return False
        if self.state == CredentialState.COOLDOWN or self.state == CredentialState.FAILED:
            if self.cooldown_until_timestamp and now >= self.cooldown_until_timestamp:
                self.state = CredentialState.AVAILABLE
                self.cooldown_until_timestamp = None
                logger.info(f"Gemini credential '{self.key_id}' cooldown expired. Restored to AVAILABLE.")
                return True
            return False
        return True

    def to_health_model(self) -> CredentialHealth:
        last_used_str = (
            datetime.fromtimestamp(self.last_used_timestamp, timezone.utc).isoformat()
            if self.last_used_timestamp
            else None
        )
        cooldown_str = (
            datetime.fromtimestamp(self.cooldown_until_timestamp, timezone.utc).isoformat()
            if self.cooldown_until_timestamp
            else None
        )
        return CredentialHealth(
            key_id=self.key_id,
            state=self.state,
            failure_count=self.failure_count,
            total_requests=self.total_requests,
            last_used=last_used_str,
            cooldown_until=cooldown_str,
            last_error=self.last_error,
        )


class GeminiCredentialManager:
    """Centralized manager for rotated Google Gemini API credentials."""

    def __init__(self, keys: Optional[List[str]] = None):
        self._slots: Dict[str, GeminiCredentialSlot] = {}
        self._current_index = 0
        self.reload_credentials(keys)

    def reload_credentials(self, keys: Optional[List[str]] = None) -> None:
        """Initialize or reload credentials from settings or provided list."""
        raw_keys = keys if keys is not None else [
            settings.gemini_api_key_1,
            settings.gemini_api_key_2,
            settings.gemini_api_key_3,
            settings.gemini_api_key_4,
        ]

        self._slots.clear()
        for idx in range(4):
            key_id = f"gemini-key-{idx + 1}"
            raw_key = raw_keys[idx] if idx < len(raw_keys) and raw_keys[idx] else ""
            self._slots[key_id] = GeminiCredentialSlot(key_id, raw_key.strip() if raw_key else "")

        active_count = sum(1 for s in self._slots.values() if s.state == CredentialState.AVAILABLE)
        logger.info(f"Loaded {active_count}/4 active Gemini credentials.")

    @property
    def has_available_credentials(self) -> bool:
        now = time.time()
        return any(slot.is_usable(now) for slot in self._slots.values())

    @property
    def configured_count(self) -> int:
        return sum(1 for slot in self._slots.values() if slot.state != CredentialState.UNCONFIGURED)

    @property
    def available_count(self) -> int:
        now = time.time()
        return sum(1 for slot in self._slots.values() if slot.is_usable(now))

    def get_credential(self) -> Tuple[str, str]:
        """
        Select an available credential using round-robin rotation.
        Returns tuple of (key_id, raw_key).
        Raises CredentialUnavailableError if no usable credentials exist.
        """
        now = time.time()
        slot_list = list(self._slots.values())
        total_slots = len(slot_list)

        for _ in range(total_slots):
            slot = slot_list[self._current_index % total_slots]
            self._current_index = (self._current_index + 1) % total_slots

            if slot.is_usable(now):
                slot.state = CredentialState.ACTIVE
                slot.last_used_timestamp = now
                slot.total_requests += 1
                return slot.key_id, slot.raw_key

        raise CredentialUnavailableError("No active Gemini API credentials available (all unconfigured or in cooldown).")

    async def mark_success(self, key_id: str) -> None:
        """Mark a request using the given credential as successful."""
        if key_id in self._slots:
            slot = self._slots[key_id]
            if slot.state == CredentialState.ACTIVE:
                slot.state = CredentialState.AVAILABLE
            slot.last_error = None

    async def mark_failed(
        self,
        key_id: str,
        error: str,
        is_quota: bool = False,
        cooldown_seconds: int = 60,
    ) -> None:
        """
        Mark a credential as failed and place it into temporary cooldown.
        Publishes AI_CREDENTIAL_FAILED event.
        """
        if key_id in self._slots:
            slot = self._slots[key_id]
            slot.failure_count += 1
            slot.last_error = error
            now = time.time()

            # Quota/rate-limit errors trigger longer cooldowns
            duration = max(cooldown_seconds, 300) if is_quota else cooldown_seconds
            slot.cooldown_until_timestamp = now + duration
            slot.state = CredentialState.COOLDOWN

            logger.warning(
                f"Gemini credential '{key_id}' failed: {error}. Placed in COOLDOWN for {duration}s."
            )

            await event_bus.publish(
                "AI_CREDENTIAL_FAILED",
                {
                    "key_id": key_id,
                    "error": error,
                    "is_quota": is_quota,
                    "cooldown_until": slot.cooldown_until_timestamp,
                },
            )

    def get_health_summary(self) -> List[CredentialHealth]:
        """Return safe health diagnostics for all 4 credential slots."""
        now = time.time()
        for slot in self._slots.values():
            slot.is_usable(now)  # Trigger automatic expiry check
        return [slot.to_health_model() for slot in self._slots.values()]


# Global singleton instance of GeminiCredentialManager
gemini_credentials = GeminiCredentialManager()
