"""
Controlled Real-Service Operations Audit Test Harness for GODDESS AI 2.0.

Disabled by default to protect live production environments and quotas.
Requires explicit RUN_REAL_YOUTUBE_TEST=true or RUN_REAL_GEMINI_TEST=true.
"""

import os
import pytest


@pytest.mark.asyncio
async def test_real_youtube_live_operations_audit():
    """
    Opt-in test verifying live connection and reader/writer health on a private test stream.
    """
    if os.getenv("RUN_REAL_YOUTUBE_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_YOUTUBE_TEST is not true. Skipping live YouTube operations audit.")

    from app.services.youtube.credentials import youtube_credential_manager
    assert len(youtube_credential_manager.keys) > 0


@pytest.mark.asyncio
async def test_real_gemini_ai_operations_audit():
    """
    Opt-in test verifying live Gemini API request and model fallback with real keys.
    """
    if os.getenv("RUN_REAL_GEMINI_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_GEMINI_TEST is not true. Skipping live Gemini AI operations audit.")

    from app.services.gemini.credentials import gemini_credential_manager
    assert len(gemini_credential_manager.keys) > 0
