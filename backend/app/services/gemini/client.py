"""
Asynchronous Gemini REST API Client for GODDESS AI 2.0.

Provides HTTP communication with Google Gemini Generative Language API (v1beta),
handling request construction, timeouts, error normalization, and mockable transport.
"""

from typing import Any, Dict, Optional, Tuple
import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.gemini.exceptions import (
    AuthenticationError,
    EmptyResponseError,
    GeminiAPIError,
    InvalidRequestError,
    ModelUnavailableError,
    QuotaExceededError,
    RateLimitError,
    RequestTimeoutError,
)

logger = get_logger("gemini.client")

BASE_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAPIClient:
    """Async API Client for Google Gemini API."""

    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        default_timeout: Optional[float] = None,
    ):
        self._http_client = http_client
        self.default_timeout = default_timeout or settings.gemini_request_timeout

    async def _get_client(self, timeout: float) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(timeout=timeout)

    async def generate_content(
        self,
        prompt: str,
        model: str,
        raw_key: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[str, Optional[str], Optional[Dict[str, int]]]:
        """
        Calls Gemini generateContent endpoint.
        Returns tuple of (generated_text, finish_reason, token_usage).
        Raises typed Gemini exceptions on failure or empty candidate content.
        """
        if not prompt or not prompt.strip():
            raise InvalidRequestError(400, "Prompt text cannot be empty.")

        timeout_sec = timeout or self.default_timeout
        endpoint_url = f"{BASE_GEMINI_URL}/{model}:generateContent"
        params = {"key": raw_key}

        # Build payload adhering to Gemini REST API specification
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt.strip()}]
                }
            ],
            "generationConfig": {
                "temperature": temperature if temperature is not None else settings.gemini_temperature,
                "maxOutputTokens": max_output_tokens if max_output_tokens is not None else settings.gemini_max_output_tokens,
            },
        }

        if system_instruction and system_instruction.strip():
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction.strip()}]
            }

        client = await self._get_client(timeout_sec)

        try:
            response = await client.post(endpoint_url, params=params, json=payload, timeout=timeout_sec)

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])

                if not candidates:
                    raise EmptyResponseError(f"Gemini returned 0 candidates for model '{model}'.")

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")
                content = candidate.get("content", {})
                parts = content.get("parts", [])

                # Extract and combine text parts
                extracted_text = "".join(part.get("text", "") for part in parts).strip()

                if not extracted_text:
                    raise EmptyResponseError(
                        f"Gemini candidate returned empty text (finishReason: {finish_reason})."
                    )

                # Extract token usage if available
                usage_meta = data.get("usageMetadata", {})
                token_usage = None
                if usage_meta:
                    token_usage = {
                        "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                        "candidates_tokens": usage_meta.get("candidatesTokenCount", 0),
                        "total_tokens": usage_meta.get("totalTokenCount", 0),
                    }

                return extracted_text, finish_reason, token_usage

            # Map HTTP error codes into structured typed exceptions
            error_data = {}
            try:
                error_data = response.json().get("error", {})
            except Exception:
                pass

            error_message = error_data.get("message", response.text)
            error_status = error_data.get("status", "")

            if response.status_code == 400:
                raise InvalidRequestError(400, error_message, error_status)

            if response.status_code == 401:
                raise AuthenticationError(401, error_message, error_status)

            if response.status_code == 403:
                raise QuotaExceededError(403, error_message, error_status)

            if response.status_code == 404:
                raise ModelUnavailableError(f"Model '{model}' not found: {error_message}")

            if response.status_code == 429 or error_status == "RESOURCE_EXHAUSTED":
                raise RateLimitError(429, error_message, error_status)

            raise GeminiAPIError(response.status_code, error_message, error_status)

        except httpx.TimeoutException as exc:
            logger.warning(f"Gemini API request timed out after {timeout_sec}s for model '{model}'.")
            raise RequestTimeoutError(f"Gemini API request timed out after {timeout_sec}s.") from exc

        except httpx.RequestError as exc:
            logger.warning(f"Gemini network error: {str(exc)}")
            raise GeminiAPIError(500, f"Network request error: {str(exc)}") from exc


# Global singleton instance of GeminiAPIClient
gemini_client = GeminiAPIClient()
