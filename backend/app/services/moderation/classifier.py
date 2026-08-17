"""
Gemini AI Moderation Classifier for Contextual Live Chat Analysis.

Uses the centralized Gemini AI Engine to classify nuanced or ambiguous live chat messages
and strictly parses structured JSON responses with fail-safe error handling.
"""

import json
import re
from typing import Optional

from app.core.logging import get_logger
from app.services.gemini.manager import GeminiAIManager, gemini_manager
from app.services.gemini.models import (
    AIRequest,
    AIRequestPriority,
    AIResponseStatus,
)
from app.services.moderation.models import (
    ActionSeverity,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
    ModerationSource,
    UserRole,
)
from app.services.youtube.models import ChatMessage

logger = get_logger("moderation.classifier")

MODERATION_SYSTEM_INSTRUCTION = """
You are the AI Live Chat Moderation Analyst for Goddess AI 2.0.
Analyze the provided live stream viewer chat message and categorize it.
Distinguish playful gaming/streaming banter from actual toxic violations.

Allowed Categories:
SAFE, SPAM, FLOOD, REPEATED_MESSAGE, SCAM, MALICIOUS_LINK, HARASSMENT, INSULT, THREAT, HATEFUL_CONTENT, SEXUAL_CONTENT, SELF_HARM_RELATED, IMPERSONATION, OTHER.

Allowed Severities:
LOW, MEDIUM, HIGH, CRITICAL.

Allowed Actions:
NONE, LOG, WARN, SLOW_MODE, DELETE, TIMEOUT, BLOCK, ESCALATE_TO_MODERATOR.

You MUST respond strictly with a valid JSON object matching this schema:
{
  "category": "SAFE",
  "confidence": 0.95,
  "severity": "LOW",
  "reason": "Harmless gaming chat message",
  "recommended_action": "NONE"
}
"""


class GeminiModerationClassifier:
    """Classifies live chat messages using centralized Gemini AI manager."""

    def __init__(self, ai_manager: Optional[GeminiAIManager] = None):
        self.ai_manager = ai_manager or gemini_manager

    def _parse_ai_json(self, raw_text: str) -> Optional[dict]:
        """Extract and parse JSON from AI response text."""
        try:
            # Direct parse
            return json.loads(raw_text.strip())
        except Exception:
            pass

        # Try regex search for embedded JSON block
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                pass
        return None

    async def classify(
        self, msg: ChatMessage, role: UserRole = UserRole.USER
    ) -> ModerationDecision:
        """
        Classifies a chat message using Gemini.
        Returns ModerationDecision. Applies fail-safe on any AI errors or empty outputs.
        """
        stream_id = msg.stream_id
        author_id = msg.author_id
        text = msg.message_text

        prompt = f'Viewer "{msg.author_name}" (Role: {role.value}) sent: "{text}"'

        ai_req = AIRequest(
            stream_id=stream_id,
            source="moderation_classifier",
            prompt=prompt,
            system_instruction=MODERATION_SYSTEM_INSTRUCTION,
            priority=AIRequestPriority.HIGH,
            temperature=0.2,  # Low temperature for deterministic classification
            max_output_tokens=256,
        )

        try:
            ai_resp = await self.ai_manager.request(ai_req)

            if ai_resp.status != AIResponseStatus.SUCCESS or not ai_resp.text:
                logger.warning(
                    f"Gemini moderation request failed or was empty ({ai_resp.status}). Applying FAIL-SAFE."
                )
                return self._create_failsafe_decision(msg, role, f"AI status: {ai_resp.status.value}")

            parsed = self._parse_ai_json(ai_resp.text)
            if not parsed or not isinstance(parsed, dict):
                logger.warning(f"Gemini returned non-JSON moderation response: {ai_resp.text[:100]}. Applying FAIL-SAFE.")
                return self._create_failsafe_decision(msg, role, "Malformed AI JSON output")

            # Parse and validate categories and actions
            cat_str = str(parsed.get("category", "SAFE")).upper()
            category = ModerationCategory[cat_str] if cat_str in ModerationCategory.__members__ else ModerationCategory.OTHER

            conf_val = float(parsed.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, conf_val))

            sev_str = str(parsed.get("severity", "LOW")).upper()
            severity = ActionSeverity[sev_str] if sev_str in ActionSeverity.__members__ else ActionSeverity.LOW

            act_str = str(parsed.get("recommended_action", "NONE")).upper()
            action = ModerationAction[act_str] if act_str in ModerationAction.__members__ else ModerationAction.NONE

            reason = str(parsed.get("reason", "AI analysis completed"))

            return ModerationDecision(
                message_id=msg.message_id,
                stream_id=stream_id,
                author_id=author_id,
                author_name=msg.author_name,
                user_role=role,
                category=category,
                confidence=confidence,
                severity=severity,
                reason=reason,
                recommended_action=action,
                source=ModerationSource.GEMINI_AI,
            )

        except Exception as exc:
            logger.error(f"Error during Gemini moderation classification: {exc}", exc_info=True)
            return self._create_failsafe_decision(msg, role, f"Exception: {str(exc)}")

    def _create_failsafe_decision(
        self, msg: ChatMessage, role: UserRole, reason: str
    ) -> ModerationDecision:
        """Create a safe fallback decision that will not execute destructive actions."""
        return ModerationDecision(
            message_id=msg.message_id,
            stream_id=msg.stream_id,
            author_id=msg.author_id,
            author_name=msg.author_name,
            user_role=role,
            category=ModerationCategory.ANALYSIS_FAILED,
            confidence=0.0,
            severity=ActionSeverity.LOW,
            reason=f"Analysis Failed ({reason})",
            recommended_action=ModerationAction.NONE,
            source=ModerationSource.GEMINI_AI,
        )


# Global singleton instance of GeminiModerationClassifier
gemini_moderation_classifier = GeminiModerationClassifier()
