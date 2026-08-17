"""
Tests for Gemini Model Failover (gemini-2.5-flash -> gemini-2.5-flash-lite) in GODDESS AI 2.0.
"""

from app.services.gemini.exceptions import GeminiAPIError, ModelUnavailableError
from app.services.gemini.models import AIRequest
from app.services.gemini.router import ModelRouter


def test_model_router_fallback_on_503_overload():
    """Verify 503 Overload triggers fallback to gemini-2.5-flash-lite."""
    router = ModelRouter(primary_model="gemini-2.5-flash", fallback_model="gemini-2.5-flash-lite")

    req = AIRequest(stream_id="STREAM_1", prompt="Hello")
    assert router.select_model(req, use_fallback=False) == "gemini-2.5-flash"
    assert router.select_model(req, use_fallback=True) == "gemini-2.5-flash-lite"

    # 503 triggers fallback
    error_503 = GeminiAPIError(message="Service Unavailable", status_code=503)
    assert router.should_fallback(error_503) is True

    # 401 should NOT trigger model fallback (it's auth)
    error_401 = GeminiAPIError(message="Unauthorized", status_code=401)
    assert router.should_fallback(error_401) is False
