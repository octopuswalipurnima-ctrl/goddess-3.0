"""
Centralized AI Moderation Manager for GODDESS AI 2.0.

Subscribes to live chat events, orchestrates deterministic rule pre-processing,
invokes Gemini AI classification when required, applies ActionPolicy gates,
supports DRY_RUN mode and automatic circuit breakers, and records audit logs.
"""

from typing import Any, Dict, Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.moderation.actions import YouTubeModerationExecutor, moderation_executor
from app.services.moderation.audit import ModerationAuditLogger, moderation_audit_logger
from app.services.moderation.classifier import GeminiModerationClassifier, gemini_moderation_classifier
from app.services.moderation.models import (
    ActionSeverity,
    ActionStatus,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
    ModerationMetrics,
    ModerationSource,
    StreamModerationConfig,
    UserRole,
)
from app.services.moderation.policy import ActionPolicy, action_policy
from app.services.moderation.rules import RuleEngine, rule_engine
from app.services.youtube.models import ChatMessage

logger = get_logger("moderation.manager")


class ModerationManager:
    """Central coordinator for stream chat moderation."""

    def __init__(
        self,
        rules: Optional[RuleEngine] = None,
        classifier: Optional[GeminiModerationClassifier] = None,
        policy: Optional[ActionPolicy] = None,
        executor: Optional[YouTubeModerationExecutor] = None,
        audit_logger: Optional[ModerationAuditLogger] = None,
    ):
        self.rules = rules or rule_engine
        self.classifier = classifier or gemini_moderation_classifier
        self.policy = policy or action_policy
        self.executor = executor or moderation_executor
        self.audit_logger = audit_logger or moderation_audit_logger

        self.metrics = ModerationMetrics()
        # stream_id -> StreamModerationConfig
        self._configs: Dict[str, StreamModerationConfig] = {}
        self._is_subscribed = False

    def get_config(self, stream_id: str) -> StreamModerationConfig:
        """Fetch or initialize moderation settings for a specific stream."""
        if stream_id not in self._configs:
            self._configs[stream_id] = StreamModerationConfig()
        return self._configs[stream_id]

    def update_config(self, stream_id: str, updates: Dict[str, Any]) -> StreamModerationConfig:
        """Update moderation configuration for a stream."""
        current = self.get_config(stream_id)
        data = current.model_dump()
        data.update(updates)
        updated_cfg = StreamModerationConfig(**data)
        self._configs[stream_id] = updated_cfg
        logger.info(f"Updated moderation configuration for stream '{stream_id}'.")
        return updated_cfg

    def reset_circuit_breaker(self, stream_id: str) -> StreamModerationConfig:
        """Explicitly reset the circuit breaker for a stream."""
        cfg = self.get_config(stream_id)
        self.policy.reset_circuit_breaker(stream_id, cfg)
        return cfg

    def start(self) -> None:
        """Subscribe to incoming CHAT_MESSAGE events on Event Bus."""
        if not self._is_subscribed:
            event_bus.subscribe("CHAT_MESSAGE", self.handle_chat_message)
            self._is_subscribed = True
            logger.info("ModerationManager subscribed to CHAT_MESSAGE events.")

    def _determine_user_role(self, msg: ChatMessage) -> UserRole:
        """Extract user role from chat message metadata."""
        if msg.is_chat_owner:
            return UserRole.OWNER
        if msg.is_chat_moderator:
            return UserRole.MODERATOR
        if msg.is_chat_sponsor:
            return UserRole.MEMBER
        return UserRole.USER

    async def handle_chat_message(self, event_data: Dict[str, Any]) -> Optional[ModerationDecision]:
        """
        Event Bus handler for incoming live chat messages.
        Runs full 3-tier moderation pipeline.
        """
        try:
            msg = ChatMessage(**event_data)
        except Exception as exc:
            logger.warning(f"Failed to deserialize ChatMessage for moderation: {exc}")
            return None

        return await self.process_message(msg)

    async def process_message(self, msg: ChatMessage) -> ModerationDecision:
        """
        Processes a single chat message through rule evaluation, AI classification, policy, and execution.
        """
        self.metrics.messages_analyzed += 1
        stream_id = msg.stream_id
        config = self.get_config(stream_id)
        role = self._determine_user_role(msg)

        # 1. Tier 1: High-Speed Deterministic Rule Engine
        decision = self.rules.evaluate(msg, role)

        if decision:
            self.metrics.rule_matches += 1
        else:
            # 2. Tier 2/3: Contextual AI Classification (if enabled and rules did not match)
            if config.enabled and config.ai_enabled:
                decision = await self.classifier.classify(msg, role)
                if decision.category not in [ModerationCategory.SAFE, ModerationCategory.ANALYSIS_FAILED]:
                    self.metrics.ai_classifications += 1
                elif decision.category == ModerationCategory.ANALYSIS_FAILED:
                    self.metrics.ai_failures += 1
            else:
                # Default safe decision
                decision = ModerationDecision(
                    message_id=msg.message_id,
                    stream_id=stream_id,
                    author_id=msg.author_id,
                    author_name=msg.author_name,
                    user_role=role,
                    category=ModerationCategory.SAFE,
                    confidence=1.0,
                    severity=ActionSeverity.LOW,
                    reason="Message is clean",
                    recommended_action=ModerationAction.NONE,
                    source=ModerationSource.RULE_ENGINE,
                )

        # Publish initial decision created event
        await event_bus.publish("MODERATION_DECISION_CREATED", decision.model_dump())

        # 3. Policy & Safety Controller Evaluation
        from app.core.safety_controller import safety_controller
        can_mod, safety_reason = safety_controller.can_moderate(stream_id)
        if not can_mod:
            self.metrics.actions_blocked += 1
            await self.audit_logger.record_audit(
                decision=decision,
                action_taken=ModerationAction.LOG,
                action_status=ActionStatus.BLOCKED,
                block_reason=safety_reason,
            )
            return decision

        approved, effective_action, block_reason = self.policy.evaluate_action(decision, config)

        if not approved:
            self.metrics.actions_blocked += 1
            if "Circuit Breaker" in (block_reason or ""):
                self.metrics.circuit_breaker_trips += 1
                await event_bus.publish("MODERATION_CIRCUIT_BREAKER_TRIPPED", {
                    "stream_id": stream_id,
                    "reason": block_reason,
                })
            await self.audit_logger.record_audit(
                decision=decision,
                action_taken=effective_action,
                action_status=ActionStatus.BLOCKED,
                block_reason=block_reason,
            )
            return decision

        # 4. Action Execution or DRY_RUN Handling
        if effective_action != ModerationAction.NONE:
            self.metrics.actions_approved += 1

            if config.dry_run:
                # DRY_RUN MODE: Record what would happen, but DO NOT execute real YouTube action
                self.metrics.actions_dry_run += 1
                logger.info(
                    f"[DRY_RUN] Moderation action '{effective_action.value}' approved for message '{decision.message_id}' (User: '{decision.author_name}'). Skipping real YouTube execution."
                )
                await self.audit_logger.record_audit(
                    decision=decision,
                    action_taken=effective_action,
                    action_status=ActionStatus.DRY_RUN,
                    block_reason="DRY_RUN mode active: action was evaluated but not sent to YouTube",
                )
            else:
                # Real Automated Execution
                try:
                    action_status = await self.executor.execute(decision, effective_action)
                    self.metrics.actions_executed += 1
                    await self.audit_logger.record_audit(
                        decision=decision,
                        action_taken=effective_action,
                        action_status=action_status,
                    )
                except Exception as exc:
                    self.metrics.actions_failed += 1
                    await self.audit_logger.record_audit(
                        decision=decision,
                        action_taken=effective_action,
                        action_status=ActionStatus.FAILED,
                        block_reason=str(exc),
                    )
        else:
            # Clean safe message
            await self.audit_logger.record_audit(
                decision=decision,
                action_taken=ModerationAction.NONE,
                action_status=ActionStatus.APPROVED,
            )

        return decision


# Global singleton instance of ModerationManager
moderation_manager = ModerationManager()
