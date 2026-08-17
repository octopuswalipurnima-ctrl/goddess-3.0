"""
Real Service Integration Audit: Google Gemini AI API for GODDESS AI 2.0.
"""

import os
import pytest
from app.services.gemini.client import gemini_client
from app.services.gemini.credentials import gemini_credentials


def test_gemini_credential_pool_loading():
    """Verify Gemini credentials pool loads from environment safely with zero secret exposure."""
    summary = gemini_credentials.get_health_summary()
    assert isinstance(summary, list)
    assert len(summary) == 4
    for slot in summary:
        assert hasattr(slot, "key_id")
        assert hasattr(slot, "state")
    assert "AIzaSy" not in str(summary)


@pytest.mark.asyncio
async def test_real_gemini_api_when_opted_in():
    """
    Real Gemini API live integration check.
    Only runs when RUN_REAL_GEMINI_TEST=true is explicitly configured in environment.
    """
    if os.getenv("RUN_REAL_GEMINI_TEST", "").lower() != "true":
        pytest.skip("RUN_REAL_GEMINI_TEST is not true. Skipping real Gemini API call.")

    try:
        key_id, raw_key = gemini_credentials.get_credential()
    except Exception:
        pytest.skip("No Gemini credentials available.")

    text, tokens = await gemini_client.generate_content(
        prompt="Respond with the single word: OK",
        model="gemini-2.5-flash",
    )
    assert text is not None
    assert len(text.strip()) > 0
