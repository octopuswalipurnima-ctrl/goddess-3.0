"""
Response Policy Gate for Safety, Cooldowns, Deduplication, and Intent Validation.

Evaluates every prospective AI Co-Host response against master toggles,
emergency stop status, intent confidence, cooldown windows, deduplication, and safety filters.
"""

import re
from typing import Optional, Tuple

from app.core.logging import get_logger
from app.services.cohost.cooldowns import CoHostCooldownTracker, cohost_cooldown_tracker
from app.services.cohost.deduplication import ResponseDeduplicator, response_deduplicator
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostResponse,
    IntentType,
    ResponseStatus,
)

logger = get_logger("cohost.policy")

# Safety blacklist patterns (API keys, credentials, prompt leak attempts)
UNSAFE_RESPONSE_PATTERNS = re.compile(
    r"(AIzaSy[a-zA-Z0-9_-]{33}|[a-zA-Z0-9_-]{32,64}\.apps\.googleusercontent\.com|"
    r"DATABASE_URL|GEMINI_API_KEY|YOUTUBE_API_KEY|system_instruction|bearer\s+[a-zA-Z0-9._-]+|"
    r"I banned that user|I have checked your account|executing shell command)",
    re.IGNORECASE,
)


class ResponsePolicy:
    """Evaluates Co-Host decisions against creator configuration and safety constraints."""

    def __init__(
        self,
        cooldown_tracker: Optional[CoHostCooldownTracker] = None,
        deduplicator: Optional[ResponseDeduplicator] = None,
    ):
        self.cooldowns = cooldown_tracker or cohost_cooldown_tracker
        self.deduplicator = deduplicator or response_deduplicator

    def evaluate_intent(
        self,
        msg: CoHostMessage,
        intent: CoHostIntent,
        config: CoHostConfig,
    ) -> Tuple[bool, Optional[str]]:
        """
        Pre-check before AI generation: should we generate a response for this intent?
        """
        # 1. Master enable toggle
        if not config.enabled:
            return False, "Co-Host is disabled for this stream"

        # 2. Emergency Stop
        if config.emergency_stop:
            return False, "Emergency stop is active on this stream"

        # 3. Intent Type Checks
        if intent.intent_type == IntentType.IGNORE:
            return False, "Message categorized as IGNORE (noise / too short)"

        if intent.intent_type == IntentType.COMMAND_REQUEST:
            return False, "Command requests are reserved for the Command module"

        if intent.intent_type == IntentType.UNKNOWN and not msg.is_mention:
            return False, "Unknown intent without direct mention"

        # 4. Configured Category Toggles
        if msg.is_mention and not config.respond_to_mentions:
            return False, "Mention responses are disabled in configuration"

        if msg.is_question and not config.respond_to_questions:
            return False, "Question responses are disabled in configuration"

        if not msg.is_mention and not msg.is_question and not config.respond_to_relevant_messages:
            return False, "General conversation responses are disabled in configuration"

        # 5. Minimum Intent Confidence Threshold (e.g. 0.70)
        if intent.confidence < config.minimum_confidence:
            return False, f"Intent confidence ({intent.confidence:.2f}) is below minimum threshold ({config.minimum_confidence:.2f})"

        # 6. Pre-check Cooldowns
        allowed, reason = self.cooldowns.check_cooldowns(
            stream_id=msg.stream_id,
            author_id=msg.author_id,
            global_cooldown=config.global_response_cooldown,
            user_cooldown=config.per_user_response_cooldown,
            max_per_minute=config.max_responses_per_minute,
            max_per_user=config.max_responses_per_user,
        )
        if not allowed:
            return False, reason

        return True, None

    def evaluate_response(
        self,
        response: CoHostResponse,
        config: CoHostConfig,
    ) -> Tuple[bool, Optional[str]]:
        """
        Post-generation check: is the generated response safe and approved for posting?
        """
        if response.status == ResponseStatus.FAILED:
            return False, response.block_reason or "Response generation failed"

        text = response.response_text.strip()
        if not text:
            return False, "Generated response was empty"

        # 1. Check Safety Patterns
        if UNSAFE_RESPONSE_PATTERNS.search(text):
            logger.critical(f"Blocked unsafe Co-Host output for stream '{response.stream_id}': Pattern match.")
            return False, "Response contained forbidden system pattern or credentials"

        # 2. Check Deduplication
        if self.deduplicator.is_duplicate(response.stream_id, text):
            return False, "Response is duplicate of a recent reply in this stream"

        # 3. Final cooldown check & record
        allowed, reason = self.cooldowns.check_cooldowns(
            stream_id=response.stream_id,
            author_id=response.author_id,
            global_cooldown=config.global_response_cooldown,
            user_cooldown=config.per_user_response_cooldown,
            max_per_minute=config.max_responses_per_minute,
            max_per_user=config.max_responses_per_user,
        )
        if not allowed:
            return False, reason

        # Record cooldown and deduplication state
        self.cooldowns.record_response(response.stream_id, response.author_id)
        self.deduplicator.record_response(response.stream_id, text)

        return True, None


# Global singleton response policy
response_policy = ResponsePolicy()
