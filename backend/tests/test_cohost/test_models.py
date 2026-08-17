"""
Tests for AI Co-Host Data Models and Configuration Defaults.
"""

import pytest
from app.services.cohost.models import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostPersonality,
    CoHostResponse,
    IntentType,
    ResponseStatus,
)


def test_cohost_config_defaults():
    """
    CRITICAL: Verify default configuration matches opt-in requirements:
    enabled = False, dry_run = True, bounded limits (20 stream, 5 user, 200 chars).
    """
    config = CoHostConfig()
    assert config.enabled is False
    assert config.dry_run is True
    assert config.emergency_stop is False
    assert config.context_window_size == 20
    assert config.user_context_window_size == 5
    assert config.max_response_length == 200
    assert config.global_response_cooldown == 5.0
    assert config.per_user_response_cooldown == 30.0
    assert config.max_responses_per_minute == 12
    assert config.max_responses_per_user == 3
    assert config.minimum_confidence == 0.70


def test_cohost_personality_defaults():
    """Verify default persona settings."""
    persona = CoHostPersonality()
    assert persona.name == "Goddess"
    assert persona.tone == "friendly"
    assert persona.style == "energetic"
    assert persona.humor_level == "moderate"
    assert persona.formality == "casual"
    assert persona.energy == "high"
    assert persona.language == "auto"
    assert persona.custom_instructions == ""


def test_cohost_intent_model():
    """Verify CoHostIntent construction and validation."""
    intent = CoHostIntent(
        intent_type=IntentType.QUESTION,
        confidence=0.85,
        reason="Interrogative phrasing detected",
    )
    assert intent.intent_type == IntentType.QUESTION
    assert intent.confidence == 0.85
    assert intent.source == "RULE_ENGINE"
