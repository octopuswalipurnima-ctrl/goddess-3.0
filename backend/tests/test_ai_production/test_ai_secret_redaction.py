"""
Tests for Zero Secret Exposure in AI Subsystem in GODDESS AI 2.0.
"""

from app.services.ai.models import AIDecision
from app.services.gemini.credentials import GeminiCredentialManager


def test_zero_secret_in_ai_decision_and_telemetry():
    """Verify AIDecision model and credential managers never expose raw API keys."""
    decision = AIDecision(
        decision_id="dec_secret_test",
        stream_id="STREAM_1",
        message_id="msg_1",
        reason="Clean message evaluated",
    )
    dumped = decision.model_dump()
    text_repr = str(dumped)

    assert "api_key" not in dumped
    assert "token" not in dumped
    assert "password" not in dumped

    # Credential Manager safe summary
    mgr = GeminiCredentialManager(keys=["AIzaSySecretSampleKey1234567890123456"])
    summary = mgr.get_health_summary()
    assert "AIzaSySecretSampleKey1234567890123456" not in str(summary)
