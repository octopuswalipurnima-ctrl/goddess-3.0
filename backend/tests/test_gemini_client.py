"""
Tests for GeminiAPIClient with Mock HTTP Transports.
"""

import pytest
import httpx
from app.services.gemini.client import GeminiAPIClient
from app.services.gemini.exceptions import (
    AuthenticationError,
    EmptyResponseError,
    InvalidRequestError,
    QuotaExceededError,
    RateLimitError,
    RequestTimeoutError,
)


@pytest.mark.asyncio
async def test_gemini_client_generate_success():
    """Verify parsing of valid Gemini generateContent response."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello! I am Goddess AI assistant."}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 15,
                "candidatesTokenCount": 8,
                "totalTokenCount": 23,
            },
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = GeminiAPIClient(http_client=http_client)

    text, finish_reason, usage = await client.generate_content(
        prompt="Introduce yourself",
        model="gemini-2.5-flash",
        raw_key="FakeKey",
    )

    assert text == "Hello! I am Goddess AI assistant."
    assert finish_reason == "STOP"
    assert usage["total_tokens"] == 23


@pytest.mark.asyncio
async def test_gemini_client_empty_response_handling():
    """Verify that empty candidate text raises EmptyResponseError."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "   "}]},
                    "finishReason": "SAFETY",
                }
            ]
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = GeminiAPIClient(http_client=http_client)

    with pytest.raises(EmptyResponseError):
        await client.generate_content(prompt="Test", model="gemini-2.5-flash", raw_key="FakeKey")


@pytest.mark.asyncio
async def test_gemini_client_error_mappings():
    """Verify HTTP status code mappings into typed exceptions."""
    # 400 Bad Request
    c400 = GeminiAPIClient(
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(400, json={"error": {"message": "Invalid prompt"}}))
        )
    )
    with pytest.raises(InvalidRequestError):
        await c400.generate_content(prompt="Test", model="m", raw_key="k")

    # 401 Unauthorized
    c401 = GeminiAPIClient(
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(401, json={"error": {"message": "Bad API key"}}))
        )
    )
    with pytest.raises(AuthenticationError):
        await c401.generate_content(prompt="Test", model="m", raw_key="k")

    # 403 Quota Exceeded
    c403 = GeminiAPIClient(
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(403, json={"error": {"message": "Quota exceeded"}}))
        )
    )
    with pytest.raises(QuotaExceededError):
        await c403.generate_content(prompt="Test", model="m", raw_key="k")

    # 429 Rate Limit
    c429 = GeminiAPIClient(
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(429, json={"error": {"message": "Rate limit"}}))
        )
    )
    with pytest.raises(RateLimitError):
        await c429.generate_content(prompt="Test", model="m", raw_key="k")
