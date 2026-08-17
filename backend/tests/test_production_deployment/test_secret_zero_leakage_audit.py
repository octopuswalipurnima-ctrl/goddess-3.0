"""
Zero Secret Leakage Audit Tests for GODDESS AI 2.0.
"""

from app.core.production_health import production_health_service
from app.services.gemini.credentials import gemini_credentials
from app.services.youtube.credentials import youtube_credentials


def test_production_health_and_credentials_zero_secret_audit():
    """Verify aggregated production health and credential summaries never contain raw secrets."""
    health = production_health_service.get_system_production_health()
    health_text = str(health.model_dump())

    # Verify no raw keys or password substrings
    assert "AIzaSy" not in health_text
    assert "password" not in health_text
    assert "secret_key" not in health_text

    yt_summary = str([slot.model_dump() for slot in youtube_credentials.get_health_summary()])
    assert "AIzaSy" not in yt_summary

    g_summary = str([slot.model_dump() for slot in gemini_credentials.get_health_summary()])
    assert "AIzaSy" not in g_summary
