"""
Rule-First Intent Detection Engine for AI Co-Host in GODDESS AI 2.0.

Provides fast, deterministic pattern matching to categorize viewer intent
(Mentions, Questions, Greetings, Commands, Compliments, Thanks, Join Requests)
with calibrated confidence (0.0 to 1.0) before engaging expensive AI generation.
"""

import re
from typing import Optional

from app.core.logging import get_logger
from app.services.cohost.models import CoHostIntent, CoHostMessage, IntentType

logger = get_logger("cohost.intents")

# Mention triggers (case-insensitive)
MENTION_PATTERNS = [
    r"@?[a-zA-Z0-9_-]+\b",
    r"@?goddess\b",
    r"@?godess\b",
    r"@?goddess_ai\b",
    r"@?ai\b",
    r"@?assistant\b",
]

# Command patterns
COMMAND_REGEX = re.compile(r"^(!|/|\$)[a-zA-Z0-9_-]+", re.IGNORECASE)

# Greeting patterns (allows leading mentions or punctuation)
GREETING_REGEX = re.compile(
    r"\b(hi|hello|hey|greetings|hola|namaste|sup|yo|good\s+(morning|afternoon|evening))\b",
    re.IGNORECASE,
)

# Thanks patterns
THANKS_REGEX = re.compile(
    r"\b(thank\s+you|thanks|thx|ty|appreciate\s+it)\b",
    re.IGNORECASE,
)

# Compliment patterns
COMPLIMENT_REGEX = re.compile(
    r"\b(great\s+stream|love\s+this|awesome\s+(stream|gameplay|bot)|you('re|\s+are)\s+(cool|amazing|the\s+best|smart|funny))\b",
    re.IGNORECASE,
)

# Join request patterns
JOIN_REGEX = re.compile(
    r"\b(can\s+i\s+join|let\s+me\s+play|room\s+code|team\s+code|lobby\s+id|add\s+me\s+in\s+game)\b",
    re.IGNORECASE,
)

# Question interrogatives
QUESTION_INTERROGATIVES = [
    r"\b(what|who|where|when|why|how|which|whose|whom)\b",
    r"\b(can\s+you|could\s+you|would\s+you|should\s+i|do\s+you|is\s+(it|this|there|he|she))\b",
]


class RuleIntentDetector:
    """Deterministic, lightweight intent classification engine."""

    def __init__(self, mention_triggers: Optional[list[str]] = None):
        triggers = mention_triggers or [
            r"@\w+",
            r"\bgoddess\b",
            r"\bgodess\b",
            r"\bgoddess_ai\b",
            r"\bai\b",
            r"\bassistant\b",
            r"\bbot\b",
        ]
        self._mention_regex = re.compile("|".join(triggers), re.IGNORECASE)

    def detect_intent(self, msg: CoHostMessage, persona_name: Optional[str] = None) -> CoHostIntent:
        """
        Detect viewer intent from message content and structure.
        Produces calibrated confidence scores (0.0 to 1.0).
        """
        text = msg.message_text.strip()
        if not text:
            return CoHostIntent(
                intent_type=IntentType.IGNORE,
                confidence=1.0,
                reason="Empty message text",
                source="RULE_ENGINE",
            )

        # 1. Very short messages / single emoji noise
        if len(text) <= 2 and not text.endswith("?"):
            return CoHostIntent(
                intent_type=IntentType.IGNORE,
                confidence=0.95,
                reason="Message is too short to warrant a conversational reply",
                source="RULE_ENGINE",
            )

        # 2. Command Requests (!help, !discord, !stats)
        if COMMAND_REGEX.match(text):
            return CoHostIntent(
                intent_type=IntentType.COMMAND_REQUEST,
                confidence=0.95,
                reason="Message starts with command prefix symbol",
                source="RULE_ENGINE",
            )

        # Check mention presence (including configured persona name if available)
        has_mention = bool(self._mention_regex.search(text))
        if persona_name and re.search(rf"@?{re.escape(persona_name)}\b", text, re.IGNORECASE):
            has_mention = True
        msg.is_mention = has_mention

        # 3. Direct Mentions + Greetings
        if GREETING_REGEX.search(text):
            confidence = 0.90 if has_mention else 0.82
            return CoHostIntent(
                intent_type=IntentType.GREETING,
                confidence=confidence,
                reason="Viewer greeted the stream or co-host",
                source="RULE_ENGINE",
            )

        # 4. Compliments / Appreciation
        if COMPLIMENT_REGEX.search(text):
            confidence = 0.88 if has_mention else 0.80
            return CoHostIntent(
                intent_type=IntentType.COMPLIMENT,
                confidence=confidence,
                reason="Viewer offered a compliment or positive feedback",
                source="RULE_ENGINE",
            )

        # 5. Expressions of Thanks
        if THANKS_REGEX.search(text):
            confidence = 0.90 if has_mention else 0.80
            return CoHostIntent(
                intent_type=IntentType.THANKS,
                confidence=confidence,
                reason="Viewer expressed gratitude",
                source="RULE_ENGINE",
            )

        # 6. Join Game / Lobby Requests
        if JOIN_REGEX.search(text):
            return CoHostIntent(
                intent_type=IntentType.JOIN_REQUEST,
                confidence=0.85,
                reason="Viewer requested to join stream gameplay or lobby",
                source="RULE_ENGINE",
            )

        # 7. Questions
        is_question = text.endswith("?") or any(re.search(pat, text, re.IGNORECASE) for pat in QUESTION_INTERROGATIVES)
        msg.is_question = is_question

        if is_question:
            confidence = 0.90 if has_mention else 0.80
            return CoHostIntent(
                intent_type=IntentType.QUESTION,
                confidence=confidence,
                reason="Interrogative phrasing or question mark detected",
                source="RULE_ENGINE",
            )

        # 8. Direct Mention without other specific intent
        if has_mention:
            return CoHostIntent(
                intent_type=IntentType.MENTION,
                confidence=0.85,
                reason="Viewer directly addressed the co-host",
                source="RULE_ENGINE",
            )

        # 9. General Conversation / Unknown
        return CoHostIntent(
            intent_type=IntentType.CONVERSATION if len(text) > 20 else IntentType.UNKNOWN,
            confidence=0.50,
            reason="No explicit deterministic intent trigger matched",
            source="RULE_ENGINE",
        )


# Global singleton rule intent detector
rule_intent_detector = RuleIntentDetector()
