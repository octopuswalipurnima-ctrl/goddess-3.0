"""
Tests for Zero Secret Exposure & Key Redaction in GODDESS AI 2.0.
"""

from app.core.provider_errors import sanitize_error_message
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.youtube.credentials import YouTubeCredentialManager


def test_sanitize_error_message_google_api_key():
    """Verify Google/Gemini/YouTube API keys are stripped from error strings."""
    raw = "Failed call to https://generativelanguage.googleapis.com/v1beta?key=AIzaSyDdummyKey12345678901234567890123 with error"
    sanitized = sanitize_error_message(raw)

    assert "AIzaSyDdummyKey12345678901234567890123" not in sanitized
    assert "[REDACTED" in sanitized


def test_sanitize_error_message_bearer_token():
    """Verify Bearer tokens are stripped from error strings."""
    raw = "HTTP 401 Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret"
    sanitized = sanitize_error_message(raw)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    assert "Bearer [REDACTED]" in sanitized


def test_youtube_health_summary_has_no_raw_keys():
    """Verify health summary objects never contain raw API keys."""
    raw_keys = ["AIzaSySecretYTKey111111111111111111", "AIzaSySecretYTKey222222222222222222"]
    mgr = YouTubeCredentialManager(keys=raw_keys)
    summary = mgr.get_health_summary()

    for item in summary:
        dumped = item.model_dump()
        assert "raw_key" not in dumped
        for val in dumped.values():
            assert val not in raw_keys


def test_gemini_health_summary_has_no_raw_keys():
    """Verify Gemini health summary objects never contain raw API keys."""
    raw_keys = ["AIzaSySecretGKey111111111111111111", "AIzaSySecretGKey222222222222222222"]
    mgr = GeminiCredentialManager(keys=raw_keys)
    summary = mgr.get_health_summary()

    for item in summary:
        dumped = item.model_dump()
        assert "raw_key" not in dumped
        for val in dumped.values():
            assert val not in raw_keys
