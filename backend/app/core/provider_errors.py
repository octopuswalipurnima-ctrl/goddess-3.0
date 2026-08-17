"""
Safe Normalized Provider Error Classification for GODDESS AI 2.0.

Classifies YouTube and Gemini API exceptions and HTTP responses into standard error codes,
sanitizes error messages, and ensures zero credential or header leakage in logs and telemetry.
"""

from enum import Enum
import re
from typing import Any, Optional, Tuple


class ProviderErrorCode(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


def sanitize_error_message(msg: str) -> str:
    """
    Strips potential API keys, auth headers, and bearer tokens from error strings.
    """
    if not msg:
        return "Unknown error"
    
    sanitized = str(msg)
    # Redact generic key query params: key=... or api_key=...
    sanitized = re.sub(r"(?i)(key|api_key|token|secret|password)=([^\s&]+)", r"\1=[REDACTED]", sanitized)
    # Redact Google/YouTube/Gemini API keys (e.g. AIzaSy...)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_API_KEY]", sanitized)
    # Redact Bearer tokens
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9\-\._~+/]+=*", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()


def classify_provider_error(
    error: Any,
    status_code: Optional[int] = None,
) -> Tuple[ProviderErrorCode, str, bool]:
    """
    Normalizes a provider error into (code, sanitized_message, is_quota).
    
    Returns:
        Tuple[ProviderErrorCode, str, bool]:
            - code: Normalized ProviderErrorCode enum
            - message: Sanitized safe string
            - is_quota: Boolean indicating if this is quota-exhaustion related
    """
    error_str = sanitize_error_message(str(error)) if error else "Unknown error"
    error_lower = error_str.lower()

    # 1. Inspect HTTP status code if provided
    if status_code is not None:
        if status_code == 429:
            if "quota" in error_lower or "resource" in error_lower or "exhausted" in error_lower or "limit" in error_lower:
                return ProviderErrorCode.QUOTA_EXHAUSTED, error_str, True
            return ProviderErrorCode.RATE_LIMITED, error_str, False
        if status_code == 403:
            if "quota" in error_lower or "limit" in error_lower or "dailylimitexceeded" in error_lower:
                return ProviderErrorCode.QUOTA_EXHAUSTED, error_str, True
            return ProviderErrorCode.PERMISSION_DENIED, error_str, False
        if status_code == 401:
            return ProviderErrorCode.AUTHENTICATION_FAILED, error_str, False
        if status_code in (408, 504):
            return ProviderErrorCode.TIMEOUT, error_str, False
        if status_code == 503:
            return ProviderErrorCode.PROVIDER_UNAVAILABLE, error_str, False
        if status_code in (400, 422):
            return ProviderErrorCode.INVALID_REQUEST, error_str, False

    # 2. Inspect text clues / exception names
    if "quota" in error_lower or "quotaexceeded" in error_lower or "dailylimitexceeded" in error_lower or "resource exhausted" in error_lower:
        return ProviderErrorCode.QUOTA_EXHAUSTED, error_str, True

    if "rate limit" in error_lower or "ratelimited" in error_lower or "too many requests" in error_lower:
        return ProviderErrorCode.RATE_LIMITED, error_str, False

    if "unauthenticated" in error_lower or "invalid_api_key" in error_lower or "api_key_invalid" in error_lower or "unauthorized" in error_lower:
        return ProviderErrorCode.AUTHENTICATION_FAILED, error_str, False

    if "permission" in error_lower or "forbidden" in error_lower or "access_denied" in error_lower:
        return ProviderErrorCode.PERMISSION_DENIED, error_str, False

    if "timeout" in error_lower or "timed out" in error_lower or "deadline exceeded" in error_lower:
        return ProviderErrorCode.TIMEOUT, error_str, False

    if "connection" in error_lower or "network" in error_lower or "connecterror" in error_lower or "unreachable" in error_lower:
        return ProviderErrorCode.NETWORK_ERROR, error_str, False

    if "unavailable" in error_lower or "overloaded" in error_lower or "service unavailable" in error_lower:
        return ProviderErrorCode.PROVIDER_UNAVAILABLE, error_str, False

    if "bad request" in error_lower or "invalid argument" in error_lower:
        return ProviderErrorCode.INVALID_REQUEST, error_str, False

    return ProviderErrorCode.UNKNOWN, error_str, False
