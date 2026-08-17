"""
Tests for ModelRouter and Fallback Decision Logic.
"""

import pytest
from app.services.gemini.exceptions import (
    AuthenticationError,
    GeminiAPIError,
    ModelUnavailableError,
    QuotaExceededError,
)
from app.services.gemini.models import AIRequest
from app.services.gemini.router import ModelRouter


def test_model_router_defaults():
    """Verify primary and fallback model defaults."""
    router = ModelRouter(primary_model="gemini-2.5-flash", fallback_model="gemini-2.5-flash-lite")
    req = AIRequest(stream_id="s1", prompt="Hello")

    # Primary model selection
    assert router.select_model(req, use_fallback=False) == "gemini-2.5-flash"

    # Fallback model selection
    assert router.select_model(req, use_fallback=True) == "gemini-2.5-flash-lite"


def test_model_preference_override():
    """Verify that explicit request preference overrides router defaults."""
    router = ModelRouter()
    req = AIRequest(stream_id="s1", prompt="Hello", model_preference="custom-model-exp")

    assert router.select_model(req, use_fallback=False) == "custom-model-exp"
    assert router.select_model(req, use_fallback=True) == "custom-model-exp"


def test_should_fallback_decision():
    """Verify error classification for model fallback decisions."""
    router = ModelRouter()

    # 503 Service Unavailable -> Fallback
    assert router.should_fallback(GeminiAPIError(503, "Model Overloaded")) is True

    # 500 Internal Error -> Fallback
    assert router.should_fallback(GeminiAPIError(500, "Internal Server Error")) is True

    # ModelUnavailableError -> Fallback
    assert router.should_fallback(ModelUnavailableError("Model not found")) is True

    # 401 Unauthorized -> NO Fallback (credential issue, not model issue)
    assert router.should_fallback(AuthenticationError(401, "Invalid API key")) is False

    # 403 Quota Exceeded -> NO Fallback (quota issue, rotate credentials instead)
    assert router.should_fallback(QuotaExceededError(403, "Daily quota exceeded")) is False
