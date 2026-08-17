"""
Tests for Safe Provider Error Classification in GODDESS AI 2.0.
"""

from app.core.provider_errors import ProviderErrorCode, classify_provider_error


def test_classify_http_status_codes():
    """Verify HTTP status codes map to normalized ProviderErrorCode enums."""
    code, _, is_quota = classify_provider_error("Resource exhausted", status_code=429)
    assert code == ProviderErrorCode.QUOTA_EXHAUSTED
    assert is_quota is True

    code, _, is_quota = classify_provider_error("Daily limit exceeded", status_code=403)
    assert code == ProviderErrorCode.QUOTA_EXHAUSTED
    assert is_quota is True

    code, _, is_quota = classify_provider_error("Forbidden", status_code=403)
    assert code == ProviderErrorCode.PERMISSION_DENIED
    assert is_quota is False

    code, _, is_quota = classify_provider_error("Invalid API Key", status_code=401)
    assert code == ProviderErrorCode.AUTHENTICATION_FAILED
    assert is_quota is False

    code, _, is_quota = classify_provider_error("Gateway Timeout", status_code=504)
    assert code == ProviderErrorCode.TIMEOUT
    assert is_quota is False

    code, _, is_quota = classify_provider_error("Service Unavailable", status_code=503)
    assert code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert is_quota is False

    code, _, is_quota = classify_provider_error("Bad Request", status_code=400)
    assert code == ProviderErrorCode.INVALID_REQUEST
    assert is_quota is False


def test_classify_text_clues():
    """Verify error string text clues without HTTP status code."""
    code, _, is_quota = classify_provider_error("QuotaExceededError: out of quota tokens")
    assert code == ProviderErrorCode.QUOTA_EXHAUSTED
    assert is_quota is True

    code, _, _ = classify_provider_error("Connection refused by host")
    assert code == ProviderErrorCode.NETWORK_ERROR

    code, _, _ = classify_provider_error("Request timed out after 10.0s")
    assert code == ProviderErrorCode.TIMEOUT
