"""
Centralized AI Decision Engine for GODDESS AI 2.0.

Orchestrates live chat analysis, moderation, AI Co-Host reply generation,
and budget accounting under the core invariant: SAFE STOP > UNSAFE AUTOMATION.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.safety_controller import safety_controller
from app.services.ai.models import AIActionType, AIConfig, AIDecision
from app.services.cohost.manager import CoHostManager, cohost_manager
from app.services.gemini.credentials import gemini_credentials
from app.services.moderation.manager import ModerationManager, moderation_manager
from app.services.moderation.models import ModerationAction
from app.services.youtube.models import ChatMessage

logger = get_logger("ai.decision_engine")


class AIDecisionEngine:
    """Central AI Decision Pipeline coordinating Moderation and Co-Host subsystems."""

    def __init__(
        self,
        mod_mgr: Optional[ModerationManager] = None,
        co_mgr: Optional[CoHostManager] = None,
    ):
        self.mod_mgr = mod_mgr or moderation_manager
        self.co_mgr = co_mgr or cohost_manager
        self._stream_configs: Dict[str, AIConfig] = {}
        self._stream_tokens_used: Dict[str, int] = {}
        self._stream_requests_used: Dict[str, int] = {}
        self._lock = asyncio.Lock()

        # Metrics
        self.total_decisions = 0
        self.moderation_decisions = 0
        self.cohost_decisions = 0
        self.fail_closed_count = 0
        self.budget_exceeded_count = 0

    def get_stream_config(self, stream_id: str) -> AIConfig:
        """Get or initialize per-stream AI configuration."""
        if stream_id not in self._stream_configs:
            self._stream_configs[stream_id] = AIConfig(stream_id=stream_id)
        return self._stream_configs[stream_id]

    def update_stream_config(self, stream_id: str, updates: Dict[str, Any]) -> AIConfig:
        """Update per-stream AI intelligence configuration."""
        current = self.get_stream_config(stream_id)
        data = current.model_dump()
        data.update(updates)
        updated = AIConfig(**data)
        self._stream_configs[stream_id] = updated
        logger.info(f"Updated AIConfig for stream '{stream_id}': {updates}")
        return updated

    def check_and_increment_budget(self, stream_id: str, estimated_tokens: int = 150) -> bool:
        """Verify stream is within daily request & token budgets."""
        config = self.get_stream_config(stream_id)
        current_reqs = self._stream_requests_used.get(stream_id, 0)
        current_tokens = self._stream_tokens_used.get(stream_id, 0)

        if current_reqs >= config.daily_request_budget:
            self.budget_exceeded_count += 1
            logger.warning(f"Stream '{stream_id}' exceeded daily request budget ({config.daily_request_budget}).")
            return False

        if current_tokens >= config.daily_token_budget:
            self.budget_exceeded_count += 1
            logger.warning(f"Stream '{stream_id}' exceeded daily token budget ({config.daily_token_budget}).")
            return False

        self._stream_requests_used[stream_id] = current_reqs + 1
        self._stream_tokens_used[stream_id] = current_tokens + estimated_tokens
        return True

    async def evaluate_message(self, message: ChatMessage) -> AIDecision:
        """
        Execute full centralized AI decision pipeline for an incoming chat message.
        """
        start_time = time.perf_counter()
        stream_id = message.stream_id
        config = self.get_stream_config(stream_id)
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        self.total_decisions += 1

        # 1. Global / Stream Emergency & Safe Mode Check via SafetyController
        if safety_controller.is_stream_emergency(stream_id):
            self.fail_closed_count += 1
            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=AIActionType.FAIL_CLOSED,
                reason="Emergency Stop active on stream",
                priority="HIGH",
                should_reply=False,
                should_moderate=False,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 2. Moderation Pipeline Gate (Tier 1 -> Tier 2 -> Tier 3)
        mod_decision = await self.mod_mgr.process_message(message)
        mod_action = getattr(mod_decision, "recommended_action", getattr(mod_decision, "action", ModerationAction.NONE)) if mod_decision else ModerationAction.NONE
        if mod_decision and mod_action != ModerationAction.NONE:
            self.moderation_decisions += 1
            action_type_map = {
                ModerationAction.DELETE: AIActionType.MODERATE_DELETE,
                ModerationAction.TIMEOUT: AIActionType.MODERATE_TIMEOUT,
                ModerationAction.BLOCK: AIActionType.MODERATE_BAN,
                ModerationAction.LOG: AIActionType.MODERATE_LOG,
                ModerationAction.WARN: AIActionType.MODERATE_LOG,
                ModerationAction.SLOW_MODE: AIActionType.MODERATE_LOG,
                ModerationAction.ESCALATE_TO_MODERATOR: AIActionType.MODERATE_LOG,
            }
            ai_action = action_type_map.get(mod_action, AIActionType.MODERATE_LOG)

            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=ai_action,
                confidence=mod_decision.confidence,
                category=mod_decision.category.value if hasattr(mod_decision.category, "value") else str(mod_decision.category),
                reason=mod_decision.reason,
                priority="HIGH",
                should_moderate=True,
                should_reply=False,
                model_used=getattr(mod_decision, "model_used", None),
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 3. AI Co-Host Reply Generation
        if not config.enabled:
            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=AIActionType.SAFE_PASS,
                reason="AI Co-Host disabled on this stream",
                should_reply=False,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        can_cohost, cohost_reason = safety_controller.can_cohost(stream_id)
        if not can_cohost:
            self.fail_closed_count += 1
            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=AIActionType.FAIL_CLOSED,
                reason=f"SafetyController blocked Co-Host: {cohost_reason}",
                should_reply=False,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # Budget Check
        if not self.check_and_increment_budget(stream_id):
            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=AIActionType.FAIL_CLOSED,
                reason="Stream daily AI token or request budget reached",
                should_reply=False,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # Generate Co-Host response via CoHostManager
        cohost_resp = await self.co_mgr.handle_chat_message(message.model_dump())
        latency = round((time.perf_counter() - start_time) * 1000, 2)

        if not cohost_resp or not cohost_resp.response_text:
            return AIDecision(
                decision_id=decision_id,
                stream_id=stream_id,
                message_id=message.message_id,
                author_id=message.author_id,
                author_name=message.author_name,
                action=AIActionType.SAFE_PASS,
                reason="No Co-Host response required or generated",
                should_reply=False,
                latency_ms=latency,
            )

        self.cohost_decisions += 1
        is_dry_run = config.dry_run or (cohost_resp.status.value == "DRY_RUN" if hasattr(cohost_resp.status, "value") else False)

        return AIDecision(
            decision_id=decision_id,
            stream_id=stream_id,
            message_id=message.message_id,
            author_id=message.author_id,
            author_name=message.author_name,
            action=AIActionType.COHOST_DRY_RUN if is_dry_run else AIActionType.COHOST_REPLY,
            confidence=1.0,
            category="cohost_reply",
            reason=f"Co-Host reply generated ({'DRY_RUN' if is_dry_run else 'LIVE'})",
            priority="NORMAL",
            should_reply=not is_dry_run,
            reply_text=cohost_resp.response_text,
            model_used=cohost_resp.model,
            fallback_used=cohost_resp.fallback_used if hasattr(cohost_resp, "fallback_used") else False,
            latency_ms=latency,
        )


# Global singleton instance
ai_decision_engine = AIDecisionEngine()
