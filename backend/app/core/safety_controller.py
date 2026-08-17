"""
Production Safety Controller for GODDESS AI 2.0.

Centralizes safety state management, emergency halts, safe mode gates, dependency
safety evaluations, and automated action permissions across all live streams.
Enforces the core operational rule: SAFE STOP > UNSAFE AUTOMATION.
"""

from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, Optional, Tuple

from app.core.events import event_bus
from app.core.logging import get_logger

logger = get_logger("core.safety")


class SafetyState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class ProductionSafetyController:
    """Central controller governing live operational safety and action gating."""

    def __init__(self):
        self._global_state = SafetyState.NORMAL
        # stream_id -> SafetyState
        self._stream_states: Dict[str, SafetyState] = {}
        self._emergency_reasons: Dict[str, str] = {}
        self._emergency_triggered_by: Dict[str, str] = {}
        self._emergency_timestamps: Dict[str, float] = {}
        self._safe_mode_reasons: Dict[str, str] = {}
        self._blocked_action_count = 0
        self._emergency_stop_count = 0

    @property
    def global_state(self) -> SafetyState:
        return self._global_state

    @property
    def is_global_emergency(self) -> bool:
        return self._global_state == SafetyState.EMERGENCY_STOP

    @property
    def is_global_safe_mode(self) -> bool:
        return self._global_state in (SafetyState.SAFE_MODE, SafetyState.EMERGENCY_STOP)

    @property
    def is_shutting_down(self) -> bool:
        return self._global_state == SafetyState.SHUTTING_DOWN

    def get_stream_state(self, stream_id: str) -> SafetyState:
        """Returns effective safety state for a specific stream."""
        if self._global_state in (SafetyState.EMERGENCY_STOP, SafetyState.SHUTTING_DOWN):
            return self._global_state
        return self._stream_states.get(stream_id, self._global_state)

    def is_stream_emergency(self, stream_id: str) -> bool:
        """Check if emergency stop is active globally or on a specific stream."""
        if self._global_state == SafetyState.EMERGENCY_STOP:
            return True
        return self._stream_states.get(stream_id) == SafetyState.EMERGENCY_STOP

    def is_stream_safe_mode(self, stream_id: str) -> bool:
        """Check if safe mode is active globally or on a specific stream."""
        if self.is_global_safe_mode:
            return True
        return self._stream_states.get(stream_id) in (SafetyState.SAFE_MODE, SafetyState.EMERGENCY_STOP)

    # ---------------------------------------------------------
    # Action Gating Evaluation Methods
    # ---------------------------------------------------------

    def can_moderate(self, stream_id: str) -> Tuple[bool, str]:
        """
        Evaluate whether automated moderation action execution is permitted on a stream.
        """
        if self.is_shutting_down:
            self._blocked_action_count += 1
            return False, "System is shutting down"

        if self.is_stream_emergency(stream_id):
            self._blocked_action_count += 1
            reason = self._emergency_reasons.get(stream_id, self._emergency_reasons.get("global", "Emergency Stop active"))
            return False, f"Emergency Stop is ACTIVE ({reason})"

        if self.is_stream_safe_mode(stream_id):
            # In safe mode, only read-only logging and dry-run evaluation are allowed
            return True, "Safe mode: evaluation allowed, automated destructive actions restricted"

        return True, "Allowed"

    def can_cohost(self, stream_id: str) -> Tuple[bool, str]:
        """
        Evaluate whether AI Co-Host reply generation is permitted on a stream.
        """
        if self.is_shutting_down:
            self._blocked_action_count += 1
            return False, "System is shutting down"

        if self.is_stream_emergency(stream_id):
            self._blocked_action_count += 1
            reason = self._emergency_reasons.get(stream_id, self._emergency_reasons.get("global", "Emergency Stop active"))
            return False, f"Emergency Stop is ACTIVE ({reason})"

        if self.is_stream_safe_mode(stream_id):
            self._blocked_action_count += 1
            return False, "Safe mode active: AI Co-Host generation paused"

        return True, "Allowed"

    def can_send_chat(self, stream_id: str) -> Tuple[bool, str]:
        """
        Evaluate whether outgoing live chat message delivery to YouTube is permitted.
        """
        if self.is_shutting_down:
            self._blocked_action_count += 1
            return False, "System is shutting down"

        if self.is_stream_emergency(stream_id):
            self._blocked_action_count += 1
            reason = self._emergency_reasons.get(stream_id, self._emergency_reasons.get("global", "Emergency Stop active"))
            return False, f"Emergency Stop is ACTIVE ({reason})"

        if self.is_stream_safe_mode(stream_id):
            self._blocked_action_count += 1
            return False, "Safe mode active: outgoing chat messages blocked"

        return True, "Allowed"

    def can_execute_command(self, stream_id: str) -> Tuple[bool, str]:
        """
        Evaluate whether chat command execution is permitted on a stream.
        """
        if self.is_shutting_down:
            self._blocked_action_count += 1
            return False, "System is shutting down"

        if self.is_stream_emergency(stream_id):
            self._blocked_action_count += 1
            return False, "Emergency Stop is ACTIVE on this stream"

        return True, "Allowed"

    def can_reconnect(self, stream_id: str, reconnect_count: int = 0) -> Tuple[bool, str]:
        """
        Evaluate whether stream reconnection attempt is permitted.
        """
        if self.is_shutting_down:
            return False, "System is shutting down"

        if reconnect_count > 50:
            return False, f"Reconnect attempt limit ({reconnect_count}) exceeded for stream '{stream_id}'"

        return True, "Allowed"

    # ---------------------------------------------------------
    # State Mutation & Emergency Control Methods
    # ---------------------------------------------------------

    async def trigger_emergency_stop(
        self,
        stream_id: Optional[str] = None,
        reason: str = "Emergency stop activated by operator",
        triggered_by: str = "operator",
    ) -> None:
        """
        Trigger emergency halt globally or for a specific stream.
        Immediately stops all automated outgoing actions. Idempotent.
        """
        now = time.time()
        self._emergency_stop_count += 1

        if stream_id is None:
            self._global_state = SafetyState.EMERGENCY_STOP
            self._emergency_reasons["global"] = reason
            self._emergency_triggered_by["global"] = triggered_by
            self._emergency_timestamps["global"] = now
            logger.critical(f"GLOBAL EMERGENCY STOP TRIGGERED by '{triggered_by}': {reason}")
        else:
            self._stream_states[stream_id] = SafetyState.EMERGENCY_STOP
            self._emergency_reasons[stream_id] = reason
            self._emergency_triggered_by[stream_id] = triggered_by
            self._emergency_timestamps[stream_id] = now
            logger.critical(f"EMERGENCY STOP TRIGGERED for stream '{stream_id}' by '{triggered_by}': {reason}")

        await event_bus.publish(
            "EMERGENCY_STOP",
            {
                "stream_id": stream_id or "global",
                "is_global": stream_id is None,
                "reason": reason,
                "triggered_by": triggered_by,
                "timestamp": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            },
        )

        await event_bus.publish(
            "SAFETY_STATE_CHANGED",
            {
                "stream_id": stream_id or "global",
                "state": SafetyState.EMERGENCY_STOP.value,
                "reason": reason,
            },
        )

    async def clear_emergency_stop(
        self,
        stream_id: Optional[str] = None,
        cleared_by: str = "operator",
    ) -> None:
        """
        Clear emergency halt globally or for a specific stream, restoring NORMAL state.
        """
        if stream_id is None:
            self._global_state = SafetyState.NORMAL
            self._emergency_reasons.pop("global", None)
            self._emergency_triggered_by.pop("global", None)
            self._emergency_timestamps.pop("global", None)
            logger.warning(f"GLOBAL EMERGENCY STOP CLEARED by '{cleared_by}'. Restored to NORMAL.")
        else:
            self._stream_states[stream_id] = SafetyState.NORMAL
            self._emergency_reasons.pop(stream_id, None)
            self._emergency_triggered_by.pop(stream_id, None)
            self._emergency_timestamps.pop(stream_id, None)
            logger.warning(f"Emergency stop CLEARED for stream '{stream_id}' by '{cleared_by}'. Restored to NORMAL.")

        await event_bus.publish(
            "SAFETY_STATE_CHANGED",
            {
                "stream_id": stream_id or "global",
                "state": SafetyState.NORMAL.value,
                "reason": f"Emergency stop cleared by {cleared_by}",
            },
        )

    async def enable_safe_mode(
        self,
        stream_id: Optional[str] = None,
        reason: str = "Safe mode enabled by operator",
    ) -> None:
        """
        Enter Safe Mode globally or for a specific stream.
        """
        if stream_id is None:
            self._global_state = SafetyState.SAFE_MODE
            self._safe_mode_reasons["global"] = reason
            logger.warning(f"GLOBAL SAFE MODE ENABLED: {reason}")
        else:
            self._stream_states[stream_id] = SafetyState.SAFE_MODE
            self._safe_mode_reasons[stream_id] = reason
            logger.warning(f"SAFE MODE ENABLED for stream '{stream_id}': {reason}")

        await event_bus.publish(
            "SAFETY_STATE_CHANGED",
            {
                "stream_id": stream_id or "global",
                "state": SafetyState.SAFE_MODE.value,
                "reason": reason,
            },
        )

    async def disable_safe_mode(self, stream_id: Optional[str] = None) -> None:
        """
        Disable Safe Mode, returning to NORMAL.
        """
        if stream_id is None:
            self._global_state = SafetyState.NORMAL
            self._safe_mode_reasons.pop("global", None)
            logger.info("GLOBAL SAFE MODE DISABLED. Restored to NORMAL.")
        else:
            self._stream_states[stream_id] = SafetyState.NORMAL
            self._safe_mode_reasons.pop(stream_id, None)
            logger.info(f"SAFE MODE DISABLED for stream '{stream_id}'. Restored to NORMAL.")

        await event_bus.publish(
            "SAFETY_STATE_CHANGED",
            {
                "stream_id": stream_id or "global",
                "state": SafetyState.NORMAL.value,
                "reason": "Safe mode disabled",
            },
        )

    async def reset_to_clean_state(self) -> None:
        """Reset all global and per-stream safety states back to NORMAL for clean testing."""
        self._global_state = SafetyState.NORMAL
        self._stream_states.clear()
        self._emergency_reasons.clear()
        self._emergency_triggered_by.clear()
        self._emergency_timestamps.clear()
        self._safe_mode_reasons.clear()
        self._blocked_action_count = 0

    def set_shutting_down(self) -> None:
        """Marks controller state as SHUTTING_DOWN."""
        self._global_state = SafetyState.SHUTTING_DOWN
        logger.info("ProductionSafetyController marked as SHUTTING_DOWN.")

    def get_safety_summary(self) -> Dict[str, Any]:
        """Export comprehensive safe telemetry summary."""
        return {
            "global_state": self._global_state.value,
            "is_global_emergency": self.is_global_emergency,
            "is_global_safe_mode": self.is_global_safe_mode,
            "is_shutting_down": self.is_shutting_down,
            "stream_states": {k: v.value for k, v in self._stream_states.items()},
            "emergency_reasons": self._emergency_reasons.copy(),
            "emergency_triggered_by": self._emergency_triggered_by.copy(),
            "emergency_stop_count": self._emergency_stop_count,
            "blocked_action_count": self._blocked_action_count,
        }


# Global singleton instance
safety_controller = ProductionSafetyController()
