"""
Tests for Provider Operations and Health Telemetry in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.manager import OperationsManager


def test_provider_operations_aggregates_youtube_and_gemini():
    """Verify provider operations reports credentials using safe aliases (KEY-1, etc.)."""
    mgr = OperationsManager()
    provs = mgr.get_provider_operations()

    assert "youtube" in provs
    assert "gemini" in provs

    yt = provs["youtube"]
    assert yt.provider_name == "YouTube Data API v3"

    g = provs["gemini"]
    assert g.provider_name == "Google Gemini API"
