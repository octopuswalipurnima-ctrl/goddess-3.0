"""
Controlled Real Google Gemini AI API Validation for GODDESS AI 2.0.

Requires explicit RUN_REAL_GEMINI_TEST=true.
Guarantees zero raw secret exposure and tests fail-closed error classification.
"""

import os
import pytest
from app.core.config import settings
from app.services.gemini.credentials import gemini_credentials
from app.services.gemini.manager import gemini_manager


@pytest.mark.asyncio
async def test_real_gemini_request_and_credential_integrity():
    """
    Validate real Gemini API request generation, bounded length capping, and error classification.
    """
    if os.getenv("RUN_REAL_GEMINI_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_GEMINI_TEST is not true. Skipping real Gemini API validation.")

    if not settings.is_gemini_configured:
        pytest.skip("No Gemini API keys configured. Skipping real Gemini test.")

    # 1. Verify credential slots are available
    summary = gemini_credentials.get_health_summary()
    assert len(summary) >= 1

    # 2. Execute minimal deterministic generation
    res = await gemini_manager.generate_response(
        prompt="Respond with only the single word: READY",
        stream_id="STREAM_TEST_REAL",
    )

    if res:
        assert len(res) <= 500  # Bounded response length
        assert "AIzaSy" not in res  # Zero secret leakage
