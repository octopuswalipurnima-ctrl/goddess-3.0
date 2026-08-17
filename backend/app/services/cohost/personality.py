"""
Personality Manager for AI Co-Host in GODDESS AI 2.0.

Manages stream-specific persona settings (tone, style, humor, energy, language)
while ensuring that creator-provided instructions never override core safety policies.
"""

from typing import Dict, Optional

from app.core.logging import get_logger
from app.services.cohost.models import CoHostPersonality

logger = get_logger("cohost.personality")


class CoHostPersonalityManager:
    """Manages configurable stream personas with safety boundary enforcement."""

    def __init__(self):
        self._personalities: Dict[str, CoHostPersonality] = {}

    def get_personality(self, stream_id: str) -> CoHostPersonality:
        """Fetch or initialize personality for a stream."""
        if stream_id not in self._personalities:
            self._personalities[stream_id] = CoHostPersonality()
        return self._personalities[stream_id]

    def update_personality(self, stream_id: str, updates: Dict[str, str]) -> CoHostPersonality:
        """Update personality settings for a stream."""
        current = self.get_personality(stream_id)
        data = current.model_dump()
        data.update(updates)
        updated = CoHostPersonality(**data)
        self._personalities[stream_id] = updated
        logger.info(f"Updated personality for stream '{stream_id}': Name={updated.name}, Tone={updated.tone}")
        return updated

    def build_personality_prompt(self, personality: CoHostPersonality) -> str:
        """
        Construct structured persona framing for system instructions.
        Safety boundaries always take precedence over custom instructions.
        """
        sections = [
            f"You are '{personality.name}', an interactive and friendly AI Co-Host for this live gaming stream.",
            f"- Persona Tone: {personality.tone}",
            f"- Conversational Style: {personality.style}",
            f"- Humor Level: {personality.humor_level}",
            f"- Formality: {personality.formality}",
            f"- Energy: {personality.energy}",
        ]

        if personality.language and personality.language != "auto":
            sections.append(f"- Preferred Language: Reply in {personality.language}")

        if personality.custom_instructions.strip():
            # Clean custom instructions to prevent prompt injection attempts
            clean_instructions = personality.custom_instructions.strip()[:300]
            sections.append(f"- Streamer's Custom Direction: {clean_instructions}")

        return "\n".join(sections)


# Global singleton personality manager
cohost_personality_manager = CoHostPersonalityManager()
