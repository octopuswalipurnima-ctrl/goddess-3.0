"""
Action Policy Gate for Safety Verification, Exemption Enforcement, and Circuit Breakers.

Enforces emergency kill switches, safe mode constraints, automatic action circuit breakers,
user role exemptions, confidence thresholds, and per-user cooldowns before approving actions.
"""

from collections import deque
import time
from typing import Deque, Dict, Optional, Tuple

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.moderation.models import (
    ModerationAction,
    ModerationDecision,
    ModerationSource,
    StreamModerationConfig,
    UserRole,
)

logger = get_logger("moderation.policy")


class ActionPolicy:
    """Evaluates moderation decisions against safety rules, creator policies, and circuit breakers."""

    def __init__(self):
        # (stream_id, author_id) -> last action timestamp
        self._user_action_cooldowns: Dict[Tuple[str, str], float] = {}
        # stream_id -> deque of action timestamps for minute rate limit
        self._stream_action_timestamps: Dict[str, Deque[float]] = {}
        # stream_id -> deque of action timestamps for short-window circuit breaker
        self._circuit_breaker_trackers: Dict[str, Deque[float]] = {}

    def reset_circuit_breaker(self, stream_id: str, config: StreamModerationConfig) -> None:
        """Reset the circuit breaker for a stream."""
        config.circuit_breaker_tripped = False
        if stream_id in self._circuit_breaker_trackers:
            self._circuit_breaker_trackers[stream_id].clear()
        logger.info(f"Circuit breaker manually RESET for stream '{stream_id}'.")

    def evaluate_action(
        self,
        decision: ModerationDecision,
        config: StreamModerationConfig,
    ) -> Tuple[bool, ModerationAction, Optional[str]]:
        """
        Evaluates a ModerationDecision against stream policy and circuit breaker limits.
        Returns (approved, effective_action, block_reason).
        """
        # If decision is NONE or SAFE, approve as NONE without blocking
        if decision.recommended_action == ModerationAction.NONE:
            return True, ModerationAction.NONE, None

        stream_id = decision.stream_id
        author_id = decision.author_id
        now = time.time()

        # 1. Check Master Moderation Toggle
        if not config.enabled:
            return False, ModerationAction.NONE, "Moderation is disabled on this stream"

        # 2. Check Emergency Kill Switch
        if config.kill_switch:
            return False, ModerationAction.LOG, "Emergency Kill Switch is ACTIVE (all automated actions blocked)"

        # 3. Check Automatic Action Circuit Breaker
        if config.circuit_breaker_tripped:
            return False, ModerationAction.LOG, "Automatic Circuit Breaker is TRIPPED (requires explicit reset)"

        # 4. Check Automation Toggle
        if not config.automation_enabled:
            return False, ModerationAction.LOG, "Automated moderation actions are disabled (logged for manual review)"

        # 5. Check User Role Exemptions
        if decision.user_role == UserRole.OWNER and config.owner_exempt:
            return False, ModerationAction.LOG, "Channel owner is exempt from automated moderation"

        if decision.user_role == UserRole.MODERATOR and config.moderator_exempt:
            return False, ModerationAction.LOG, "Moderator is exempt from automated moderation"

        if decision.user_role == UserRole.MEMBER and config.member_exempt:
            return False, ModerationAction.LOG, "Channel member is exempt from automated moderation"

        # 6. Check Safe Mode (Restricts actions to highest-confidence rule actions only)
        if config.safe_mode:
            if decision.source == ModerationSource.GEMINI_AI:
                return False, ModerationAction.LOG, "Safe Mode is ACTIVE: AI-driven actions are restricted to LOG"
            if decision.confidence < 0.90:
                return False, ModerationAction.LOG, f"Safe Mode is ACTIVE: Rule confidence ({decision.confidence:.2f}) < 0.90"

        # 7. Check AI Confidence Threshold
        if decision.source == ModerationSource.GEMINI_AI:
            if decision.confidence < config.ai_confidence_threshold:
                return (
                    False,
                    ModerationAction.LOG,
                    f"AI confidence ({decision.confidence:.2f}) below required threshold ({config.ai_confidence_threshold:.2f})",
                )

        # 8. Check Category Enabled Toggles
        if decision.category.value == "SPAM" and not config.spam_enabled:
            return False, ModerationAction.LOG, "SPAM moderation is disabled in configuration"
        if decision.category.value == "FLOOD" and not config.flood_enabled:
            return False, ModerationAction.LOG, "FLOOD moderation is disabled in configuration"
        if decision.category.value == "REPEATED_MESSAGE" and not config.repeat_detection_enabled:
            return False, ModerationAction.LOG, "REPEATED_MESSAGE moderation is disabled in configuration"
        if decision.category.value == "MALICIOUS_LINK" and not config.link_detection_enabled:
            return False, ModerationAction.LOG, "LINK moderation is disabled in configuration"

        # 9. Check Per-User Action Cooldown
        cooldown_key = (stream_id, author_id)
        if cooldown_key in self._user_action_cooldowns:
            last_time = self._user_action_cooldowns[cooldown_key]
            if now - last_time < config.cooldown_seconds_per_user:
                return (
                    False,
                    ModerationAction.LOG,
                    f"User action cooldown active ({now - last_time:.1f}s / {config.cooldown_seconds_per_user}s)",
                )

        # 10. Check Automatic Circuit Breaker Window (e.g. >= 10 actions in 10s)
        if stream_id not in self._circuit_breaker_trackers:
            self._circuit_breaker_trackers[stream_id] = deque()
        cb_q = self._circuit_breaker_trackers[stream_id]
        while cb_q and now - cb_q[0] > config.circuit_breaker_window_seconds:
            cb_q.popleft()

        cb_q.append(now)
        if len(cb_q) >= config.circuit_breaker_action_threshold:
            config.circuit_breaker_tripped = True
            logger.critical(
                f"AUTOMATIC CIRCUIT BREAKER TRIPPED for stream '{stream_id}'! ({len(cb_q)} actions in {config.circuit_breaker_window_seconds}s)"
            )
            return (
                False,
                ModerationAction.LOG,
                f"Automatic Circuit Breaker TRIPPED due to action storm ({len(cb_q)} actions in {config.circuit_breaker_window_seconds}s)",
            )

        # 11. Check Stream Action Rate Limit (e.g. max 30 actions / minute)
        if stream_id not in self._stream_action_timestamps:
            self._stream_action_timestamps[stream_id] = deque()
        st_q = self._stream_action_timestamps[stream_id]
        while st_q and now - st_q[0] > 60.0:
            st_q.popleft()

        if len(st_q) >= config.max_actions_per_minute:
            return (
                False,
                ModerationAction.LOG,
                f"Stream action rate limit exceeded ({len(st_q)} actions in 60s)",
            )

        # Record action execution timestamp
        self._user_action_cooldowns[cooldown_key] = now
        st_q.append(now)

        return True, decision.recommended_action, None


# Global singleton instance of ActionPolicy
action_policy = ActionPolicy()
