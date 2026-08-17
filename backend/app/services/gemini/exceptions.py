"""
Custom Exception Hierarchy for Gemini AI Engine in GODDESS AI 2.0.
"""


class GeminiEngineError(Exception):
    """Base exception for all Gemini Engine operations."""
    pass


class CredentialUnavailableError(GeminiEngineError):
    """Raised when no active Gemini API credentials are available or all are in cooldown."""
    pass


class GeminiAPIError(GeminiEngineError):
    """Raised when Gemini API returns an HTTP error."""

    def __init__(self, status_code: int, message: str, reason: str = ""):
        super().__init__(f"Gemini API Error ({status_code}): {message} [{reason}]")
        self.status_code = status_code
        self.message = message
        self.reason = reason


class QuotaExceededError(GeminiAPIError):
    """Raised when Gemini API returns 403 quotaExceeded or dailyLimitExceeded."""
    pass


class RateLimitError(GeminiAPIError):
    """Raised when Gemini API returns 429 rateLimitExceeded or RESOURCE_EXHAUSTED."""
    pass


class InvalidRequestError(GeminiAPIError):
    """Raised when Gemini API returns 400 Bad Request or malformed prompt."""
    pass


class AuthenticationError(GeminiAPIError):
    """Raised when Gemini API returns 401 Unauthorized or API_KEY_INVALID."""
    pass


class ModelUnavailableError(GeminiEngineError):
    """Raised when the requested model is not found, deprecated, or overloaded."""
    pass


class EmptyResponseError(GeminiEngineError):
    """Raised when Gemini returns an empty or blocked candidate text."""
    pass


class QueueFullError(GeminiEngineError):
    """Raised when the internal Gemini request queue has reached its maximum bounded capacity."""
    pass


class RequestTimeoutError(GeminiEngineError):
    """Raised when a Gemini API request exceeds its configured timeout deadline."""
    pass
