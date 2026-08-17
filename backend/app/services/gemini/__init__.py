"""
Gemini AI Engine Service Package for GODDESS AI 2.0.

Exports Gemini credential manager, API client, rate limiter, request queue,
model router, and centralized AI manager.
"""

from app.services.gemini.client import GeminiAPIClient, gemini_client
from app.services.gemini.credentials import (
    GeminiCredentialManager,
    gemini_credentials,
)
from app.services.gemini.manager import GeminiAIManager, gemini_manager
from app.services.gemini.models import (
    AIRequest,
    AIRequestPriority,
    AIResponse,
    AIResponseStatus,
    CredentialHealth,
    CredentialState,
    GeminiMetrics,
)
from app.services.gemini.queue import PriorityRequestQueue, gemini_queue
from app.services.gemini.rate_limiter import (
    TokenBucketRateLimiter,
    gemini_rate_limiter,
)
from app.services.gemini.router import ModelRouter, gemini_router
from app.services.gemini.exceptions import (
    AuthenticationError,
    CredentialUnavailableError,
    EmptyResponseError,
    GeminiAPIError,
    GeminiEngineError,
    InvalidRequestError,
    ModelUnavailableError,
    QueueFullError,
    QuotaExceededError,
    RateLimitError,
    RequestTimeoutError,
)

__all__ = [
    "GeminiAPIClient",
    "gemini_client",
    "GeminiCredentialManager",
    "gemini_credentials",
    "GeminiAIManager",
    "gemini_manager",
    "TokenBucketRateLimiter",
    "gemini_rate_limiter",
    "PriorityRequestQueue",
    "gemini_queue",
    "ModelRouter",
    "gemini_router",
    "AIRequest",
    "AIRequestPriority",
    "AIResponse",
    "AIResponseStatus",
    "CredentialHealth",
    "CredentialState",
    "GeminiMetrics",
    "AuthenticationError",
    "CredentialUnavailableError",
    "EmptyResponseError",
    "GeminiAPIError",
    "GeminiEngineError",
    "InvalidRequestError",
    "ModelUnavailableError",
    "QueueFullError",
    "QuotaExceededError",
    "RateLimitError",
    "RequestTimeoutError",
]
