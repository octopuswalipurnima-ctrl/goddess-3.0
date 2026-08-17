"""
Centralized AI Co-Host Manager for GODDESS AI 2.0.
Orchestrates adaptive engagement decisions, stream awareness, creator knowledge,
personality framing, Gemini generation, policy gating, and YouTube chat delivery.
"""

import time
from typing import Any, Dict, Optional
from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.safety_controller import safety_controller
from app.services.cohost.audit import CoHostAuditLogger, cohost_audit_logger
from app.services.cohost.awareness import StreamAwarenessEngine, stream_awareness_engine
from app.services.cohost.context import CoHostContextManager, cohost_context_manager
from app.services.cohost.deduplication import ResponseDeduplicator, response_deduplicator
from app.services.cohost.engagement import EngagementDecisionEngine, engagement_decision_engine
from app.services.cohost.intents import RuleIntentDetector, rule_intent_detector
from app.services.cohost.knowledge import CreatorKnowledgeManager, creator_knowledge_manager
from app.services.cohost.models import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostMessage,
    CoHostMetrics,
    CoHostResponse,
    EngagementDecision,
    EngagementResponseType,
    IntentType,
    ResponseStatus,
)
from app.services.cohost.personality import CoHostPersonalityManager, cohost_personality_manager
from app.services.cohost.response_generator import ResponseGenerator, response_generator
from app.services.cohost.response_policy import ResponsePolicy, response_policy
from app.services.youtube.models import ChatMessage
from app.services.youtube.stream_manager import StreamManager, stream_manager

logger = get_logger("cohost.manager")


class CoHostManager:
    """Central orchestrator for adaptive AI Co-Host operations across all streams."""

    def __init__(
        self,
        intent_detector: Optional[RuleIntentDetector] = None,
        engagement_engine: Optional[EngagementDecisionEngine] = None,
        context_mgr: Optional[CoHostContextManager] = None,
        personality_mgr: Optional[CoHostPersonalityManager] = None,
        awareness_engine: Optional[StreamAwarenessEngine] = None,
        knowledge_mgr: Optional[CreatorKnowledgeManager] = None,
        generator: Optional[ResponseGenerator] = None,
        policy: Optional[ResponsePolicy] = None,
        audit_logger: Optional[CoHostAuditLogger] = None,
        yt_stream_mgr: Optional[StreamManager] = None,
        deduplicator: Optional[ResponseDeduplicator] = None,
    ):
        self.intent_detector = intent_detector or rule_intent_detector
        self.engagement_engine = engagement_engine or engagement_decision_engine
        self.context_mgr = context_mgr or cohost_context_manager
        self.personality_mgr = personality_mgr or cohost_personality_manager
        self.awareness = awareness_engine or stream_awareness_engine
        self.knowledge = knowledge_mgr or creator_knowledge_manager
        self.generator = generator or response_generator
        self.policy = policy or response_policy
        self.audit_logger = audit_logger or cohost_audit_logger
        self.yt_stream_mgr = yt_stream_mgr or stream_manager
        self.deduplicator = deduplicator or response_deduplicator

        self.metrics = CoHostMetrics()
        # stream_id -> CoHostConfig
        self._configs: Dict[str, CoHostConfig] = {}
        self._is_subscribed = False

    def get_config(self, stream_id: str) -> CoHostConfig:
        """Fetch or initialize Co-Host settings for a stream."""
        if stream_id not in self._configs:
            self._configs[stream_id] = CoHostConfig()
        return self._configs[stream_id]

    def update_config(self, stream_id: str, updates: Dict[str, Any]) -> CoHostConfig:
        """Update Co-Host configuration for a stream."""
        current = self.get_config(stream_id)
        data = current.model_dump()
        data.update(updates)
        updated = CoHostConfig(**data)
        self._configs[stream_id] = updated
        logger.info(
            f"Updated Co-Host config for stream '{stream_id}': Enabled={updated.enabled}, DryRun={updated.dry_run}"
        )
        return updated

    def start(self) -> None:
        """Subscribe to incoming CHAT_MESSAGE and STREAM_ENDED events on Event Bus."""
        if not self._is_subscribed:
            event_bus.subscribe("CHAT_MESSAGE", self.handle_chat_message)
            event_bus.subscribe("STREAM_ENDED", self._handle_stream_ended)
            self._is_subscribed = True
            logger.info("CoHostManager subscribed to Event Bus.")

    async def _handle_stream_ended(self, event_data: Dict[str, Any]) -> None:
        """Clean up stream memory and caches on stream end."""
        stream_id = event_data.get("stream_id")
        if stream_id:
            self.context_mgr.clear_context(stream_id)
            self.awareness.clear_stream_awareness(stream_id)
            self.deduplicator.clear_stream_history(stream_id)
            logger.info(f"Cleaned up Co-Host runtime state for stream '{stream_id}'.")

    async def handle_chat_message(self, event_data: Dict[str, Any]) -> Optional[CoHostResponse]:
        """
        Event Bus handler for incoming live chat messages.
        Executes full adaptive Co-Host intelligence pipeline.
        """
        try:
            msg_obj = ChatMessage(**event_data)
        except Exception as exc:
            logger.warning(f"Failed to deserialize ChatMessage for Co-Host: {exc}")
            return None

        return await self.process_message(msg_obj)

    async def process_message(self, raw_msg: ChatMessage) -> Optional[CoHostResponse]:
        """
        Processes a single chat message through pre-processing, intent detection,
        engagement decision gating, context updates, Gemini generation, policy gating, and delivery.
        """
        self.metrics.messages_analyzed += 1
        stream_id = raw_msg.stream_id
        config = self.get_config(stream_id)

        # 1. Pre-process into CoHostMessage
        cohost_msg = CoHostMessage(
            stream_id=stream_id,
            channel_id=raw_msg.channel_id,
            message_id=raw_msg.message_id,
            author_id=raw_msg.author_id,
            author_name=raw_msg.author_name,
            message_text=raw_msg.message_text,
            user_role="OWNER" if raw_msg.is_chat_owner else ("MODERATOR" if raw_msg.is_chat_moderator else "USER"),
        )

        # 2. Update short-term conversational context
        ctx = self.context_mgr.get_context(
            stream_id=stream_id,
            max_stream_messages=config.context_window_size,
            max_user_messages=config.user_context_window_size,
        )
        ctx.add_viewer_message(cohost_msg)

        # 3. Intent Detection
        personality = self.personality_mgr.get_personality(stream_id) if config.personality_enabled else config.personality
        intent = self.intent_detector.detect_intent(cohost_msg, persona_name=personality.name)
        self.metrics.intents_detected += 1

        # 4. Adaptive Engagement Decision (Cost & Relevance Pre-Gating)
        engagement_decision = self.engagement_engine.evaluate_engagement(cohost_msg, intent, config)
        self.metrics.engagement_decisions += 1

        # Publish intent & engagement decision telemetry
        await event_bus.publish(
            "COHOST_INTENT_DETECTED",
            {
                "stream_id": stream_id,
                "message_id": cohost_msg.message_id,
                "author_name": cohost_msg.author_name,
                "intent": intent.model_dump(),
                "engagement_decision": engagement_decision.model_dump(),
            },
        )

        if not engagement_decision.should_respond:
            if engagement_decision.response_type == EngagementResponseType.IGNORE:
                self.metrics.messages_ignored += 1
            else:
                self.metrics.no_response_count += 1
                if any(k in engagement_decision.reason.lower() for k in ["safetycontroller", "blocked", "emergency stop", "safe mode", "cooldown"]):
                    self.metrics.responses_blocked += 1
            return None

        # 5. Safety Controller Pre-Generation Check
        can_co, co_reason = safety_controller.can_cohost(stream_id)
        if not can_co:
            self.metrics.responses_blocked += 1
            await self.audit_logger.record_audit(
                CoHostAuditRecord(
                    stream_id=stream_id,
                    message_id=cohost_msg.message_id,
                    author_id=cohost_msg.author_id,
                    author_name=cohost_msg.author_name,
                    user_message=cohost_msg.message_text,
                    intent=intent.intent_type,
                    intent_confidence=intent.confidence,
                    engagement_response_type=engagement_decision.response_type,
                    response_status=ResponseStatus.BLOCKED,
                    dry_run=config.dry_run,
                    block_reason=co_reason,
                )
            )
            return None

        # 6. Response Generation via Gemini (with Stream Awareness, Creator Knowledge, Similarity Regeneration)
        self.metrics.responses_requested += 1
        response = await self.generator.generate_response(
            cohost_msg,
            intent,
            config,
            engagement_decision=engagement_decision,
        )

        if response.status == ResponseStatus.FAILED:
            self.metrics.responses_failed += 1
            await self.audit_logger.record_audit(
                CoHostAuditRecord(
                    stream_id=stream_id,
                    message_id=cohost_msg.message_id,
                    author_id=cohost_msg.author_id,
                    author_name=cohost_msg.author_name,
                    user_message=cohost_msg.message_text,
                    intent=intent.intent_type,
                    intent_confidence=intent.confidence,
                    engagement_response_type=engagement_decision.response_type,
                    response_status=ResponseStatus.FAILED,
                    dry_run=config.dry_run,
                    latency_ms=response.latency_ms,
                    model=response.model,
                    fallback_used=response.fallback_used,
                    block_reason=response.block_reason,
                )
            )
            return response

        self.metrics.responses_generated += 1
        if response.fallback_used:
            self.metrics.gemini_fallbacks += 1

        # 7. Post-Generation Response Policy Gate
        approved, block_reason = self.policy.evaluate_response(response, config)
        if not approved:
            self.metrics.responses_blocked += 1
            response.status = ResponseStatus.BLOCKED
            response.block_reason = block_reason
            await self.audit_logger.record_audit(
                CoHostAuditRecord(
                    stream_id=stream_id,
                    message_id=cohost_msg.message_id,
                    author_id=cohost_msg.author_id,
                    author_name=cohost_msg.author_name,
                    user_message=cohost_msg.message_text,
                    intent=intent.intent_type,
                    intent_confidence=intent.confidence,
                    engagement_response_type=engagement_decision.response_type,
                    response_text=response.response_text,
                    response_status=ResponseStatus.BLOCKED,
                    dry_run=config.dry_run,
                    response_length=len(response.response_text),
                    latency_ms=response.latency_ms,
                    model=response.model,
                    fallback_used=response.fallback_used,
                    block_reason=block_reason,
                )
            )
            return response

        # 8. Record co-host response in stream conversational context
        ctx.add_cohost_response(response.response_text, persona_name=personality.name)

        # 9. Safety Controller Outgoing Chat Permission Check
        can_send_chat, chat_block_reason = safety_controller.can_send_chat(stream_id)
        if not can_send_chat:
            self.metrics.responses_blocked += 1
            response.status = ResponseStatus.BLOCKED
            response.block_reason = chat_block_reason
            await self.audit_logger.record_audit(
                CoHostAuditRecord(
                    stream_id=stream_id,
                    message_id=cohost_msg.message_id,
                    author_id=cohost_msg.author_id,
                    author_name=cohost_msg.author_name,
                    user_message=cohost_msg.message_text,
                    intent=intent.intent_type,
                    intent_confidence=intent.confidence,
                    engagement_response_type=engagement_decision.response_type,
                    response_text=response.response_text,
                    response_status=ResponseStatus.BLOCKED,
                    dry_run=config.dry_run,
                    block_reason=chat_block_reason,
                )
            )
            return response

        # 10. Dispatch based on DRY_RUN vs LIVE
        if config.dry_run:
            self.metrics.responses_dry_run += 1
            response.status = ResponseStatus.DRY_RUN
            logger.info(
                f"[CO-HOST DRY_RUN] Stream '{stream_id}' reply to '{cohost_msg.author_name}': \"{response.response_text}\""
            )
            await self.audit_logger.record_audit(
                CoHostAuditRecord(
                    stream_id=stream_id,
                    message_id=cohost_msg.message_id,
                    author_id=cohost_msg.author_id,
                    author_name=cohost_msg.author_name,
                    user_message=cohost_msg.message_text,
                    intent=intent.intent_type,
                    intent_confidence=intent.confidence,
                    engagement_response_type=engagement_decision.response_type,
                    response_text=response.response_text,
                    response_status=ResponseStatus.DRY_RUN,
                    dry_run=True,
                    response_length=len(response.response_text),
                    latency_ms=response.latency_ms,
                    model=response.model,
                    fallback_used=response.fallback_used,
                )
            )
            await event_bus.publish(
                "COHOST_DRY_RUN_RESPONSE",
                {
                    "stream_id": stream_id,
                    "message_id": cohost_msg.message_id,
                    "author_name": cohost_msg.author_name,
                    "reply_text": response.response_text,
                    "model": response.model,
                },
            )
            return response

        # LIVE MODE: Deliver live reply via LiveChatWriter
        self.metrics.responses_sent += 1
        response.status = ResponseStatus.SENT
        session = self.yt_stream_mgr.get_session(stream_id)
        if session and session.writer:
            await session.writer.post_message(response.response_text)
            logger.info(
                f"[CO-HOST LIVE] Stream '{stream_id}' posted reply to '{cohost_msg.author_name}': \"{response.response_text}\""
            )
        else:
            logger.warning(
                f"Live session or chat writer unavailable for stream '{stream_id}'. Response marked SENT."
            )

        await self.audit_logger.record_audit(
            CoHostAuditRecord(
                stream_id=stream_id,
                message_id=cohost_msg.message_id,
                author_id=cohost_msg.author_id,
                author_name=cohost_msg.author_name,
                user_message=cohost_msg.message_text,
                intent=intent.intent_type,
                intent_confidence=intent.confidence,
                engagement_response_type=engagement_decision.response_type,
                response_text=response.response_text,
                response_status=ResponseStatus.SENT,
                dry_run=False,
                response_length=len(response.response_text),
                latency_ms=response.latency_ms,
                model=response.model,
                fallback_used=response.fallback_used,
            )
        )

        await event_bus.publish(
            "COHOST_RESPONSE_SENT",
            {
                "stream_id": stream_id,
                "message_id": cohost_msg.message_id,
                "author_name": cohost_msg.author_name,
                "reply_text": response.response_text,
                "model": response.model,
            },
        )

        return response


# Global singleton instance
cohost_manager = CoHostManager()
