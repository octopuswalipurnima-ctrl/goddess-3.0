"""
Engagement Decision Engine for AI Co-Host in GODDESS AI 2.0.
Determines whether an incoming chat message warrants a response BEFORE invoking Gemini AI.
Enforces cost control, direct-mention priority, spam filtering, and probability weighting.
"""

import re
import time
from typing import Optional, Tuple
from app.core.logging import get_logger
from app.core.safety_controller import safety_controller
from app.services.cohost.awareness import StreamAwarenessEngine, stream_awareness_engine
from app.services.cohost.cooldowns import CoHostCooldownTracker, cohost_cooldown_tracker
from app.services.cohost.knowledge import CreatorKnowledgeManager, creator_knowledge_manager
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    EngagementDecision,
    EngagementResponseType,
    IntentType,
)

logger = get_logger("cohost.engagement")

QUESTION_WORDS = {"what", "when", "where", "which", "who", "why", "how", "is", "are", "can", "could", "would", "do", "does"}


class EngagementDecisionEngine:
    """Evaluates viewer messages to decide if an AI response is useful, safe, and cost-effective."""

    def __init__(
        self,
        knowledge_mgr: Optional[CreatorKnowledgeManager] = None,
        awareness_engine: Optional[StreamAwarenessEngine] = None,
        cooldown_tracker: Optional[CoHostCooldownTracker] = None,
    ):
        self.knowledge_mgr = knowledge_mgr or creator_knowledge_manager
        self.awareness = awareness_engine or stream_awareness_engine
        self.cooldowns = cooldown_tracker or cohost_cooldown_tracker

    def _is_direct_mention(self, text: str, persona_name: str) -> bool:
        """Check if message directly mentions or addresses the Co-Host persona."""
        lower_text = text.lower()
        lower_name = persona_name.lower()
        if f"@{lower_name}" in lower_text or f"hey {lower_name}" in lower_text or f"hi {lower_name}" in lower_text:
            return True
        # Direct word boundary match
        return bool(re.search(rf"\b{re.escape(lower_name)}\b", lower_text))

    def _is_question(self, text: str) -> bool:
        """Determine if message is a direct question."""
        stripped = text.strip()
        if stripped.endswith("?"):
            return True
        tokens = re.findall(r"\w+", stripped.lower())
        if tokens and tokens[0] in QUESTION_WORDS:
            return True
        return False

    def evaluate_engagement(
        self,
        msg: CoHostMessage,
        intent: CoHostIntent,
        config: CoHostConfig,
    ) -> EngagementDecision:
        """
        Execute deterministic evaluation pipeline on a chat message.
        Returns a structured EngagementDecision.
        """
        stream_id = msg.stream_id
        text = msg.message_text.strip()
        target_id = msg.message_id
        persona_name = config.personality.name

        # 1. Master enable toggle
        if not config.enabled:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                reason="Co-Host is disabled for this stream",
                target_message_id=target_id,
            )

        # 2. Config Emergency Stop
        if config.emergency_stop:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                priority="HIGH",
                reason="Emergency stop is active on this stream",
                target_message_id=target_id,
            )

        # 3. Safety Controller Emergency Stop & Safe Mode Gating
        can_co, co_reason = safety_controller.can_cohost(stream_id)
        if not can_co:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                priority="HIGH",
                reason=f"SafetyController blocked Co-Host: {co_reason}",
                target_message_id=target_id,
            )

        # 3. Stream Status Check
        aw = self.awareness.get_awareness(stream_id)
        if aw.stream_status == "ENDED":
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                reason="Stream has ended",
                target_message_id=target_id,
            )

        # 4. Message Quality / Obvious Noise Filter
        if len(text) < 2 or re.match(r"^[!/$.#]", text):
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.IGNORE,
                reason="Message too short or contains command prefix",
                target_message_id=target_id,
            )

        # Repetitive character spam (e.g. 'aaaaaaa', 'wssssss')
        if re.search(r"(.)\1{6,}", text):
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.IGNORE,
                reason="Repetitive character spam",
                target_message_id=target_id,
            )

        # 5. Direct Mention Evaluation (Priority Elevation)
        is_mention = msg.is_mention or self._is_direct_mention(text, persona_name)
        is_question = msg.is_question or self._is_question(text)

        # 6. Intent & Category Gating
        if intent.intent_type == IntentType.IGNORE:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.IGNORE,
                reason="Intent classifier labeled message as IGNORE",
                target_message_id=target_id,
            )

        if intent.intent_type == IntentType.COMMAND_REQUEST:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.DEFER,
                reason="Command request deferred to commands module",
                target_message_id=target_id,
            )

        # 7. Cooldown Evaluation
        allowed_cd, cd_reason = self.cooldowns.check_cooldowns(
            stream_id=stream_id,
            author_id=msg.author_id,
            global_cooldown=config.global_response_cooldown,
            user_cooldown=config.per_user_response_cooldown,
            max_per_minute=config.max_responses_per_minute,
            max_per_user=config.max_responses_per_user,
        )
        if not allowed_cd:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                reason=f"Cooldown active: {cd_reason}",
                target_message_id=target_id,
                cooldown_required=True,
            )

        # 8. Decision Logic based on Message Category & Mention
        if is_mention:
            if is_question:
                return EngagementDecision(
                    should_respond=True,
                    response_type=EngagementResponseType.ANSWER,
                    priority="HIGH",
                    confidence=max(0.92, intent.confidence),
                    reason="Direct mention with explicit question",
                    target_message_id=target_id,
                )
            return EngagementDecision(
                should_respond=True,
                response_type=EngagementResponseType.ACKNOWLEDGE,
                priority="HIGH",
                confidence=max(0.85, intent.confidence),
                reason="Direct mention of Co-Host persona",
                target_message_id=target_id,
            )

        if is_question:
            if not config.respond_to_questions:
                return EngagementDecision(
                    should_respond=False,
                    response_type=EngagementResponseType.NO_RESPONSE,
                    reason="Question responses disabled in configuration",
                    target_message_id=target_id,
                )
            return EngagementDecision(
                should_respond=True,
                response_type=EngagementResponseType.ANSWER,
                priority="NORMAL",
                confidence=max(0.88, intent.confidence),
                reason="Relevant stream or gameplay question",
                target_message_id=target_id,
            )

        # 9. Conversational Chatter & Response Probability Gating
        if not config.respond_to_relevant_messages:
            return EngagementDecision(
                should_respond=False,
                response_type=EngagementResponseType.NO_RESPONSE,
                reason="General conversational responses disabled in configuration",
                target_message_id=target_id,
            )

        # Respect response_probability factor for general chatter (avoid answering every message)
        if intent.intent_type in (IntentType.GREETING, IntentType.COMPLIMENT, IntentType.THANKS):
            # Useful social engagements
            return EngagementDecision(
                should_respond=True,
                response_type=EngagementResponseType.ENCOURAGE if intent.intent_type == IntentType.COMPLIMENT else EngagementResponseType.ACKNOWLEDGE,
                priority="NORMAL",
                confidence=intent.confidence,
                reason=f"Engaging with viewer {intent.intent_type.value.lower()}",
                target_message_id=target_id,
            )

        if intent.intent_type in (IntentType.STREAM_TOPIC, IntentType.GAMEPLAY, IntentType.CONVERSATION):
            if intent.confidence < config.confidence_threshold:
                return EngagementDecision(
                    should_respond=False,
                    response_type=EngagementResponseType.NO_RESPONSE,
                    reason=f"Intent confidence ({intent.confidence:.2f}) below threshold ({config.confidence_threshold:.2f})",
                    target_message_id=target_id,
                )
            return EngagementDecision(
                should_respond=True,
                response_type=EngagementResponseType.FOLLOW_UP,
                priority="NORMAL",
                confidence=intent.confidence,
                reason="Relevant conversational stream topic",
                target_message_id=target_id,
            )

        # Default fallback for unclassified chatter
        return EngagementDecision(
            should_respond=False,
            response_type=EngagementResponseType.NO_RESPONSE,
            reason="Low-value chatter / unclassified intent",
            target_message_id=target_id,
        )


# Global singleton instance
engagement_decision_engine = EngagementDecisionEngine()
