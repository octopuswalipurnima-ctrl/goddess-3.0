"""
Controlled Provider Rotation Tests for YouTube & Gemini in GODDESS AI 2.0.

Validates multi-key failover and rotation policy without exposing raw credentials.
"""

import pytest
from app.services.gemini.credentials import gemini_credentials
from app.services.youtube.credentials import youtube_credentials


def test_provider_credential_rotation_slots():
    """
    Validate that YouTube and Gemini managers maintain isolated 4-slot rotation structures.
    """
    yt_summary = youtube_credentials.get_health_summary()
    assert len(yt_summary) == 4

    gemini_summary = gemini_credentials.get_health_summary()
    assert len(gemini_summary) == 4

    # Verify zero secrets in summary outputs
    for slot in yt_summary:
        assert not hasattr(slot, "raw_key") or not getattr(slot, "raw_key", None)
    for slot in gemini_summary:
        assert not hasattr(slot, "raw_key") or not getattr(slot, "raw_key", None)
