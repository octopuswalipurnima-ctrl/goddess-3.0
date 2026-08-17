"""
Tests for Unified Provider Health Service in GODDESS AI 2.0.
"""

import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.providers.health import ProviderHealthService
from app.services.youtube.credentials import YouTubeCredentialManager


def test_youtube_provider_health_healthy():
    """Verify YouTube provider health aggregation when keys are available."""
    mgr = YouTubeCredentialManager(keys=["Key1", "Key2"])
    health = ProviderHealthService.get_youtube_provider_health()

    assert health.provider == "youtube"
    assert health.credential_count >= 0
    assert health.failure_rate >= 0.0
    assert isinstance(health.credentials, list)


def test_gemini_provider_health_healthy():
    """Verify Gemini provider health aggregation when keys are available."""
    health = ProviderHealthService.get_gemini_provider_health()

    assert health.provider == "gemini"
    assert health.credential_count >= 0
    assert isinstance(health.latency_metrics, dict)
    assert isinstance(health.credentials, list)


def test_all_providers_health_map():
    """Verify combined provider health dictionary contains both youtube and gemini."""
    all_health = ProviderHealthService.get_all_providers_health()
    assert "youtube" in all_health
    assert "gemini" in all_health
    assert all_health["youtube"].provider == "youtube"
    assert all_health["gemini"].provider == "gemini"
