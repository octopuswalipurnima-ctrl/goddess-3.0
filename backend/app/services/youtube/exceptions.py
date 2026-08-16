"""
Custom Exception Hierarchy for YouTube Engine in GODDESS AI 2.0.
"""


class YouTubeEngineError(Exception):
    """Base exception for all YouTube Engine operations."""
    pass


class CredentialUnavailableError(YouTubeEngineError):
    """Raised when no active YouTube API credentials are available or all are in cooldown."""
    pass


class YouTubeAPIError(YouTubeEngineError):
    """Raised when YouTube Data API returns an HTTP error."""

    def __init__(self, status_code: int, message: str, reason: str = ""):
        super().__init__(f"YouTube API Error ({status_code}): {message} [{reason}]")
        self.status_code = status_code
        self.message = message
        self.reason = reason


class QuotaExceededError(YouTubeAPIError):
    """Raised when YouTube API returns a 403 quotaExceeded error."""
    pass


class RateLimitError(YouTubeAPIError):
    """Raised when YouTube API returns a 429 rateLimitExceeded error."""
    pass


class StreamNotFoundError(YouTubeEngineError):
    """Raised when a requested YouTube Live Stream cannot be found or is private."""
    pass


class LiveChatUnavailableError(YouTubeEngineError):
    """Raised when live chat is disabled or unavailable for the stream."""
    pass


class MaxStreamsReachedError(YouTubeEngineError):
    """Raised when attempting to add more streams than the allowed concurrent maximum."""
    pass


class DuplicateStreamError(YouTubeEngineError):
    """Raised when attempting to create a duplicate session for an already tracked stream."""
    pass


class ChatMessageValidationError(YouTubeEngineError):
    """Raised when an outgoing chat message violates YouTube formatting/length constraints."""
    pass
