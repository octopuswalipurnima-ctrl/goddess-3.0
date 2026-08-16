"""
YouTube Service Package for GODDESS AI 2.0.

Exports centralized credential manager, async API client, stream session,
stream manager, live chat reader, and live stream detector.
"""

from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.credentials import (
    YouTubeCredentialManager,
    youtube_credentials,
)
from app.services.youtube.chat import LiveChatReader
from app.services.youtube.stream_session import StreamSession
from app.services.youtube.stream_manager import StreamManager, stream_manager
from app.services.youtube.live_detection import LiveStreamDetector, live_detector
from app.services.youtube.models import (
    ChatMessage,
    CredentialHealth,
    CredentialState,
    LiveStreamInfo,
    SessionMetrics,
    StreamSessionSummary,
    StreamStatus,
)
from app.services.youtube.exceptions import (
    ChatMessageValidationError,
    CredentialUnavailableError,
    DuplicateStreamError,
    LiveChatUnavailableError,
    MaxStreamsReachedError,
    QuotaExceededError,
    RateLimitError,
    StreamNotFoundError,
    YouTubeAPIError,
    YouTubeEngineError,
)

__all__ = [
    "YouTubeAPIClient",
    "youtube_client",
    "YouTubeCredentialManager",
    "youtube_credentials",
    "LiveChatReader",
    "StreamSession",
    "StreamManager",
    "stream_manager",
    "LiveStreamDetector",
    "live_detector",
    "ChatMessage",
    "CredentialHealth",
    "CredentialState",
    "LiveStreamInfo",
    "SessionMetrics",
    "StreamSessionSummary",
    "StreamStatus",
    "ChatMessageValidationError",
    "CredentialUnavailableError",
    "DuplicateStreamError",
    "LiveChatUnavailableError",
    "MaxStreamsReachedError",
    "QuotaExceededError",
    "RateLimitError",
    "StreamNotFoundError",
    "YouTubeAPIError",
    "YouTubeEngineError",
]
