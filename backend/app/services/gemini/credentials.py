"""
Centralized Credential & Quota Manager for Google Gemini API.

Manages up to 4 rotated Gemini API keys, tracks per-key health states and metrics,
enforces exponential cooldowns, and publishes credential lifecycle events
to the Event Bus with zero secret exposure.
"""

from datetime import datetime, timezone
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.provider_errors import ProviderErrorCode, classify_provider_error, sanitize_error_message
from app.services.gemini.exceptions import CredentialUnavailableError
from app.services.gemini.models import CredentialHealth, CredentialState

logger = get_logger("gemini.credentials")


class GeminiCredentialSlot:
    """Internal representation of a Gemini API credential slot."""

    def __init__(self, key_id: str, raw_key: str):
        self.key_id = key_id
        self.credential_id = key_id
        self.raw_key = raw_key
        self.state = (
            CredentialState.AVAILABLE
            if raw_key and raw_key.strip()
            else CredentialState.UNCONFIGURED
        )
        self.failure_count = 0
        self.consecutive_failures = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limit_failures = 0
        self.quota_failures = 0
        self.last_used_timestamp: Optional[float] = None
        self.cooldown_until_timestamp: Optional[float] = None
        self.last_error: Optional[str] = None
        self.last_error_type: Optional[str] = None

    def is_usable(self, now: float) -> bool:
        """Check whether credential is ready to serve requests, expiring cooldowns if elapsed."""
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
        """Convert internal state to safe Pydantic health model without exposing raw secrets."""
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
            credential_id=self.credential_id,
            state=self.state,
            failure_count=self.failure_count,
            consecutive_failures=self.consecutive_failures,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            rate_limit_failures=self.rate_limit_failures,
            quota_failures=self.quota_failures,
            last_used=last_used_str,
            last_used_at=last_used_str,
            cooldown_until=cooldown_str,
            last_error=self.last_error,
            last_error_type=self.last_error_type,
        )


class GeminiCredentialManager:
    """Centralized manager for rotated Google Gemini API credentials."""

    def __init__(self, keys: Optional[List[str]] = None):
        self._slots: Dict[str, GeminiCredentialSlot] = {}
        self._current_index = 0
        self.reload_credentials(keys)

    def reload_credentials(self, keys: Optional[List[str]] = None) -> None:
        """Initialize or reload credentials from settings or provided list."""
        raw_keys = (
            keys
            if keys is not None
            else [
                settings.gemini_api_key_1,
                settings.gemini_api_key_2,
                settings.gemini_api_key_3,
                settings.gemini_api_key_4,
            ]
        )

        self._slots.clear()
        for idx in range(4):
            key_id = f"gemini-key-{idx + 1}"
            raw_key = raw_keys[idx] if idx < len(raw_keys) and raw_keys[idx] else ""
            self._slots[key_id] = GeminiCredentialSlot(key_id, raw_key.strip() if raw_key else "")

        active_count = sum(1 for s in self._slots.values() if s.state == CredentialState.AVAILABLE)
        logger.info(f"Loaded {active_count}/4 active Gemini credentials.")

    @property
    def has_available_credentials(self) -> bool:
        """Check if at least one credential is currently usable."""
        now = time.time()
        return any(slot.is_usable(now) for slot in self._slots.values())

    @property
    def configured_count(self) -> int:
        """Count of slots with non-empty keys."""
        return sum(1 for slot in self._slots.values() if slot.state != CredentialState.UNCONFIGURED)

    @property
    def available_count(self) -> int:
        """Count of slots currently usable (AVAILABLE or expired cooldown)."""
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

        raise CredentialUnavailableError(
            "No active Gemini API credentials available (all unconfigured or in cooldown)."
        )

    async def mark_success(self, key_id: str) -> None:
        """Mark a request using the given credential as successful."""
        if key_id in self._slots:
            slot = self._slots[key_id]
            if slot.state == CredentialState.ACTIVE:
                slot.state = CredentialState.AVAILABLE
            slot.consecutive_failures = 0
            slot.successful_requests += 1
            slot.last_error = None
            slot.last_error_type = None

    async def mark_failed(
        self,
        key_id: str,
        error: str,
        is_quota: bool = False,
        cooldown_seconds: int = 60,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Mark a credential as failed and place it into temporary cooldown.
        Applies exponential backoff for consecutive failures.
        Publishes AI_CREDENTIAL_FAILED event.
        """
        if key_id in self._slots:
            slot = self._slots[key_id]
            slot.failure_count += 1
            slot.failed_requests += 1
            slot.consecutive_failures += 1

            code, sanitized_msg, auto_quota = classify_provider_error(error, status_code)
            is_quota_final = is_quota or auto_quota or (code == ProviderErrorCode.QUOTA_EXHAUSTED)

            if is_quota_final:
                slot.quota_failures += 1
            elif code == ProviderErrorCode.RATE_LIMITED:
                slot.rate_limit_failures += 1

            slot.last_error = sanitized_msg
            slot.last_error_type = error_type or code.value
            now = time.time()

            # Quota/rate-limit errors trigger longer base cooldowns (min 300s) with exponential backoff
            base_duration = max(cooldown_seconds, 300) if is_quota_final else max(cooldown_seconds, 15)
            backoff_multiplier = min(2 ** max(0, slot.consecutive_failures - 1), 16)
            duration = min(base_duration * backoff_multiplier, 3600)  # Max 1 hour

            slot.cooldown_until_timestamp = now + duration
            slot.state = CredentialState.COOLDOWN

            logger.warning(
                f"Gemini credential '{key_id}' failed ({slot.last_error_type}): {sanitized_msg}. "
                f"Placed in COOLDOWN for {duration}s."
            )

            await event_bus.publish(
                "AI_CREDENTIAL_FAILED",
                {
                    "key_id": key_id,
                    "credential_id": slot.credential_id,
                    "error": sanitized_msg,
                    "error_type": slot.last_error_type,
                    "is_quota": is_quota_final,
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
