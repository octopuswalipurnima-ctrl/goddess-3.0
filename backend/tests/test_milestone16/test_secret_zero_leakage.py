"""
Tests for Zero Secret Leakage Guarantees in GODDESS AI 2.0.
"""

import pytest
from app.core.config import settings
from app.core.validator import get_safe_configuration_summary
from app.services.gemini.credentials import gemini_credentials
from app.services.youtube.credentials import youtube_credentials


def test_zero_secrets_in_diagnostics_and_credentials():
    """Verify diagnostic outputs and credential summaries contain zero raw keys."""
    summary = get_safe_configuration_summary(settings)
    for k, v in summary.items():
        assert "AIzaSy" not in str(v)
        assert "secret" not in str(v).lower() or "VALID" in str(v) or "INVALID" in str(v)

    yt_diag = youtube_credentials.get_health_summary()
    for item in yt_diag:
        assert not hasattr(item, "raw_key")

    g_diag = gemini_credentials.get_health_summary()
    for item in g_diag:
        assert not hasattr(item, "raw_key")
