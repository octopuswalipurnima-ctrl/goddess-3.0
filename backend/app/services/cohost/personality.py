"""
Personality Manager for AI Co-Host in GODDESS AI 2.0.
Provides stream-scoped persona configuration with anti-injection protections.
"""

import re
from typing import Any, Dict, Optional
from app.core.logging import get_logger
from app.services.cohost.models import CoHostPersonality

logger = get_logger("cohost.personality")


class CoHostPersonalityManager:
    """Manages configurable stream personas with safety boundary enforcement and stream isolation."""

    def __init__(self):
        # stream_id -> CoHostPersonality
        self._personalities: Dict[str, CoHostPersonality] = {}

    def get_personality(self, stream_id: str) -> CoHostPersonality:
        """Fetch or initialize personality for a stream."""
        if stream_id not in self._personalities:
            self._personalities[stream_id] = CoHostPersonality(
                stream_id=stream_id,
                name="Goddess",
            )
        return self._personalities[stream_id]

    def update_personality(self, stream_id: str, updates: Dict[str, Any]) -> CoHostPersonality:
        """Update personality settings for a stream."""
        current = self.get_personality(stream_id)
        data = current.model_dump()
        data.update(updates)
        data["stream_id"] = stream_id
        updated = CoHostPersonality(**data)
        self._personalities[stream_id] = updated
        logger.info(
            f"Updated personality for stream '{stream_id}': Name={updated.name}, Tone={updated.tone}, Energy={updated.energy_level}"
        )
        return updated

    def reset_stream_personality(self, stream_id: str) -> None:
        """Reset stream personality to default."""
        self._personalities[stream_id] = CoHostPersonality(stream_id=stream_id)

    def _sanitize_custom_instructions(self, instructions: str) -> str:
        """Sanitize creator custom instructions to prevent prompt injection and policy overrides."""
        if not instructions or not instructions.strip():
            return ""

        cleaned = instructions.strip()[:300]
        # Strip system instruction override patterns
        cleaned = re.sub(
            r"(ignore\s+(all\s+)?previous\s+instructions|system\s+instruction|system\s+prompt|reveal\s+secret|developer\s+mode)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned

    def build_personality_prompt(self, personality: CoHostPersonality) -> str:
        """
        Construct structured persona framing for system instructions.
        Safety boundaries always take precedence over custom instructions.
        """
        sections = [
            f"You are '{personality.name}', the dedicated AI Co-Host for this live broadcast.",
            f"- Persona Tone: {personality.tone}",
            f"- Conversational Style: {personality.response_style or personality.style}",
            f"- Energy Level: {personality.energy_level or personality.energy}",
            f"- Humor Level: {personality.humor_level}",
            f"- Friendliness: {personality.friendliness}",
            f"- Formality: {personality.formality}",
            f"- Emoji Usage: {personality.emoji_usage}",
        ]

        if personality.language and personality.language != "auto":
            sections.append(f"- Preferred Language: Reply in {personality.language}")

        if personality.custom_instructions:
            clean_instr = self._sanitize_custom_instructions(personality.custom_instructions)
            if clean_instr:
                sections.append(f"- Streamer's Custom Direction: {clean_instr}")

        return "\n".join(sections)


# Global singleton personality manager
cohost_personality_manager = CoHostPersonalityManager()
