"""
Centralized AI Co-Host Manager for GODDESS AI 2.0.

Subscribes to live chat events, orchestrates rule-first intent detection,
manages short-term conversation context, generates conversational replies via Gemini,
enforces safety and anti-spam policy gates, and posts approved replies through YouTube chat.
"""

import time
from typing import Any, Dict, Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.cohost.audit import CoHostAuditLogger, cohost_audit_logger
from app.services.cohost.context import CoHostContextManager, cohost_context_manager
from app.services.cohost.intents import RuleIntentDetector, rule_intent_detector
from app.services.cohost.models import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostMessage,
    CoHostMetrics,
    CoHostResponse,
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
    """Central orchestrator for AI Co-Host operations."""

    def __init__(
        self,
        intent_detector: Optional[RuleIntentDetector] = None,
        context_mgr: Optional[CoHostContextManager] = None,
        personality_mgr: Optional[CoHostPersonalityManager] = None,
        generator: Optional[ResponseGenerator] = None,
        policy: Optional[ResponsePolicy] = None,
        audit_logger: Optional[CoHostAuditLogger] = None,
        yt_stream_mgr: Optional[StreamManager] = None,
    ):
        self.intent_detector = intent_detector or rule_intent_detector
        self.context_mgr = context_mgr or cohost_context_manager
        self.personality_mgr = personality_mgr or cohost_personality_manager
        self.generator = generator or response_generator
        self.policy = policy or response_policy
        self.audit_logger = audit_logger or cohost_audit_logger
        self.yt_stream_mgr = yt_stream_mgr or stream_manager

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
        logger.info(f"Updated Co-Host config for stream '{stream_id}': Enabled={updated.enabled}, DryRun={updated.dry_run}")
        return updated

    def start(self) -> None:
        """Subscribe to incoming CHAT_MESSAGE and STREAM_ENDED events on Event Bus."""
        if not self._is_subscribed:
            event_bus.subscribe("CHAT_MESSAGE", self.handle_chat_message)
            event_bus.subscribe("STREAM_ENDED", self._handle_stream_ended)
            self._is_subscribed = True
            logger.info("CoHostManager subscribed to Event Bus.")

    async def _handle_stream_ended(self, event_data: Dict[str, Any]) -> None:
        """Clean up stream memory on end."""
        stream_id = event_data.get("stream_id")
        if stream_id:
            self.context_mgr.clear_context(stream_id)

    async def handle_chat_message(self, event_data: Dict[str, Any]) -> Optional[CoHostResponse]:
        """
        Event Bus handler for incoming live chat messages.
        Runs full Co-Host pipeline independently from Moderation.
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
        context updates, Gemini generation, policy gating, and delivery.
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
        intent = self.intent_detector.detect_intent(cohost_msg, persona_name=config.personality.name)
        self.metrics.intents_detected += 1

        # Publish intent detected event
        await event_bus.publish("COHOST_INTENT_DETECTED", {
            "stream_id": stream_id,
            "message_id": cohost_msg.message_id,
            "author_name": cohost_msg.author_name,
            "intent": intent.model_dump(),
        })

        # 4. Intent Pre-Policy & Safety Controller Evaluation
        from app.core.safety_controller import safety_controller
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
                    response_status=ResponseStatus.BLOCKED,
                    dry_run=config.dry_run,
                    block_reason=co_reason,
                )
            )
            return None

        allowed, block_reason = self.policy.evaluate_intent(cohost_msg, intent, config)
        if not allowed:
            # If intent is ignored or Co-Host disabled, do not generate response
            if intent.intent_type not in [IntentType.IGNORE, IntentType.UNKNOWN]:
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
                        response_status=ResponseStatus.BLOCKED,
                        dry_run=config.dry_run,
                        block_reason=block_reason,
                    )
                )
            return None

        # 5. Response Generation via Gemini (NORMAL Priority)
        self.metrics.responses_requested += 1
        response = await self.generator.generate_response(cohost_msg, intent, config)

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
                    response_status=ResponseStatus.FAILED,
                    dry_run=config.dry_run,
                    latency_ms=response.latency_ms,
                    model=response.model,
                    block_reason=response.block_reason,
                )
            )
            return response

        self.metrics.responses_generated += 1

        # 6. Post-Generation Response Policy Gate
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
                    response_text=response.response_text,
                    response_status=ResponseStatus.BLOCKED,
                    dry_run=config.dry_run,
                    response_length=len(response.response_text),
                    latency_ms=response.latency_ms,
                    model=response.model,
                    block_reason=block_reason,
                )
            )
            return response

        # 7. Record co-host response in stream conversational context
        ctx.add_cohost_response(response.response_text, persona_name=config.personality.name)

        # 8. Dispatch based on DRY_RUN vs LIVE
        if config.dry_run:
            # DRY_RUN MODE: Record what would be sent without posting to YouTube
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
                    response_text=response.response_text,
                    response_status=ResponseStatus.DRY_RUN,
                    dry_run=True,
                    response_length=len(response.response_text),
                    latency_ms=response.latency_ms,
                    model=response.model,
                )
            )
        else:
            # LIVE POSTING via existing YouTube infrastructure
            can_chat, chat_reason = safety_controller.can_send_chat(stream_id)
            if not can_chat:
                self.metrics.responses_blocked += 1
                response.status = ResponseStatus.BLOCKED
                response.block_reason = chat_reason
                await self.audit_logger.record_audit(
                    CoHostAuditRecord(
                        stream_id=stream_id,
                        message_id=cohost_msg.message_id,
                        author_id=cohost_msg.author_id,
                        author_name=cohost_msg.author_name,
                        user_message=cohost_msg.message_text,
                        intent=intent.intent_type,
                        intent_confidence=intent.confidence,
                        response_text=response.response_text,
                        response_status=ResponseStatus.BLOCKED,
                        dry_run=False,
                        response_length=len(response.response_text),
                        latency_ms=response.latency_ms,
                        model=response.model,
                        block_reason=chat_reason,
                    )
                )
                return response

            try:
                session = self.yt_stream_mgr.get_session(stream_id)
                if session and session.is_active:
                    await session.send_chat_message(response.response_text)
                    response.status = ResponseStatus.SENT
                    self.metrics.responses_sent += 1
                    logger.info(
                        f"[CO-HOST SENT] Posted response to stream '{stream_id}': \"{response.response_text}\""
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
                            response_text=response.response_text,
                            response_status=ResponseStatus.SENT,
                            dry_run=False,
                            response_length=len(response.response_text),
                            latency_ms=response.latency_ms,
                            model=response.model,
                        )
                    )
                else:
                    raise RuntimeError(f"Stream session '{stream_id}' is not active on YouTube")
            except Exception as exc:
                self.metrics.responses_failed += 1
                response.status = ResponseStatus.FAILED
                response.block_reason = f"YouTube posting error: {exc}"
                logger.error(f"Failed to post Co-Host reply to YouTube live chat: {exc}")
                await self.audit_logger.record_audit(
                    CoHostAuditRecord(
                        stream_id=stream_id,
                        message_id=cohost_msg.message_id,
                        author_id=cohost_msg.author_id,
                        author_name=cohost_msg.author_name,
                        user_message=cohost_msg.message_text,
                        intent=intent.intent_type,
                        intent_confidence=intent.confidence,
                        response_text=response.response_text,
                        response_status=ResponseStatus.FAILED,
                        dry_run=False,
                        response_length=len(response.response_text),
                        latency_ms=response.latency_ms,
                        model=response.model,
                        block_reason=str(exc),
                    )
                )

        return response


# Global singleton instance of CoHostManager
cohost_manager = CoHostManager()
