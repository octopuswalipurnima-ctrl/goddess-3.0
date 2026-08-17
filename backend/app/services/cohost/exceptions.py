"""
Exceptions for AI Co-Host Engine in GODDESS AI 2.0.
"""


class CoHostError(Exception):
    """Base exception for all AI Co-Host errors."""
    pass


class InvalidCoHostConfigError(CoHostError):
    """Raised when Co-Host configuration values fail validation."""
    pass


class ResponseGenerationError(CoHostError):
    """Raised when response generation fails or is aborted."""
    pass


class ResponsePolicyBlockedError(CoHostError):
    """Raised when a generated response is rejected by ResponsePolicy."""
    pass


class ContextLimitExceededError(CoHostError):
    """Raised when conversational context exceeds bounded memory limits."""
    pass
