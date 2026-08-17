"""
Tests for CoHostPersonalityManager and Custom Instruction Framing.
"""

import pytest
from app.services.cohost.models import CoHostPersonality
from app.services.cohost.personality import CoHostPersonalityManager


def test_personality_manager_build_prompt():
    """Verify personality prompt incorporates name, tone, and style."""
    mgr = CoHostPersonalityManager()
    persona = CoHostPersonality(
        name="Astra",
        tone="witty",
        style="sarcastic but friendly",
        humor_level="high",
        custom_instructions="Cheer for Team Blue!",
    )

    prompt = mgr.build_personality_prompt(persona)
    assert "Astra" in prompt
    assert "witty" in prompt
    assert "Cheer for Team Blue!" in prompt


def test_personality_manager_stream_isolation():
    """Verify updating Stream A persona does not affect Stream B."""
    mgr = CoHostPersonalityManager()
    mgr.update_personality("stream_A", {"name": "Astra", "tone": "energetic"})

    persona_b = mgr.get_personality("stream_B")
    assert persona_b.name == "Goddess"
    assert persona_b.tone == "friendly"
