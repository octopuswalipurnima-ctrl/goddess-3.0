"""
Centralized Model Router for Google Gemini API.

Selects between primary model (gemini-2.5-flash) and fallback model (gemini-2.5-flash-lite),
evaluating failure causes and applying fallback policies when appropriate.
"""

from typing import Optional

from app.core.config import settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.gemini.exceptions import (
    GeminiAPIError,
    ModelUnavailableError,
)
from app.services.gemini.models import AIRequest

logger = get_logger("gemini.router")


class ModelRouter:
    """Intelligent router between primary and fallback Gemini models."""

    def __init__(
        self,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.primary_model = primary_model or settings.gemini_primary_model
        self.fallback_model = fallback_model or settings.gemini_fallback_model

    def select_model(self, request: AIRequest, use_fallback: bool = False) -> str:
        """
        Select model name for the request.
        Explicit request preference takes priority, otherwise uses primary or fallback.
        """
        if request.model_preference and request.model_preference.strip():
            return request.model_preference.strip()

        if use_fallback:
            return self.fallback_model
        return self.primary_model

    def should_fallback(self, error: Exception) -> bool:
        """
        Determines if an error warrants falling back to a lighter/alternative model.
        Model overloads, 503 Service Unavailable, or ModelUnavailable errors trigger fallback.
        Authentication (401) or Quota (403) errors do NOT trigger model fallback.
        """
        if isinstance(error, ModelUnavailableError):
            return True

        if isinstance(error, GeminiAPIError):
            # 503 (Overloaded / Unavailable), 500 (Internal Server Error), 504 (Gateway Timeout)
            if error.status_code in [500, 502, 503, 504]:
                return True
            if "not found" in error.message.lower() or "unsupported" in error.message.lower():
                return True

        return False

    async def notify_fallback(self, request_id: str, stream_id: str, reason: str) -> None:
        """Publishes AI_MODEL_FALLBACK event to the Event Bus."""
        logger.warning(
            f"Routing fallback model '{self.fallback_model}' for request '{request_id}' (Stream: {stream_id}). Reason: {reason}"
        )
        await event_bus.publish(
            "AI_MODEL_FALLBACK",
            {
                "request_id": request_id,
                "stream_id": stream_id,
                "primary_model": self.primary_model,
                "fallback_model": self.fallback_model,
                "reason": reason,
            },
        )


# Global singleton instance of ModelRouter
gemini_router = ModelRouter()
