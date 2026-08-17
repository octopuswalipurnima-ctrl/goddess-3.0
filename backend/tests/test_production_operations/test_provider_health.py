"""
Tests for Production Provider Health Telemetry in GODDESS AI 2.0.
"""

from app.core.production_health import ProductionHealthService


def test_youtube_status_safe_fields():
    """Verify YouTube provider status model contains no raw keys."""
    status = ProductionHealthService.get_youtube_status()
    assert status.name == "youtube"
    assert "configured_keys" in status.metadata

    dumped = status.model_dump()
    assert "raw_key" not in dumped
    assert "api_key" not in dumped


def test_gemini_status_safe_fields():
    """Verify Gemini provider status model contains no raw keys."""
    status = ProductionHealthService.get_gemini_status()
    assert status.name == "gemini"
    assert "primary_model" in status.metadata

    dumped = status.model_dump()
    assert "raw_key" not in dumped
    assert "api_key" not in dumped
