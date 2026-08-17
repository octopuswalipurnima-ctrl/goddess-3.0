"""
Tests for Gemini AI REST Endpoints and Health Integration.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services.gemini.models import AIResponse, AIResponseStatus


@pytest.mark.asyncio
async def test_ai_test_endpoint_validation_error():
    """Verify that empty prompt in POST /api/v1/ai/test triggers validation error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/ai/test", json={"prompt": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_ai_test_endpoint_successful_generation():
    """Verify POST /api/v1/ai/test executes through gemini_manager with mocked response."""
    mock_response = AIResponse(
        request_id="test_req_123",
        stream_id="test_stream",
        status=AIResponseStatus.SUCCESS,
        text="Goddess AI generated reply",
        model="gemini-2.5-flash",
        credential_id="gemini-key-1",
        latency_seconds=0.25,
    )

    with patch("app.api.v1.endpoints.ai.gemini_manager.request", new=AsyncMock(return_value=mock_response)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ai/test",
                json={"prompt": "Say hello to stream viewers", "stream_id": "stream_42"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SUCCESS"
            assert data["text"] == "Goddess AI generated reply"
            assert data["model"] == "gemini-2.5-flash"
            assert data["credential_id"] == "gemini-key-1"


@pytest.mark.asyncio
async def test_health_endpoint_gemini_diagnostics():
    """Verify GET /api/v1/health includes honest Gemini component metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert "gemini" in data["components"]
        gemini_comp = data["components"]["gemini"]
        assert "metadata" in gemini_comp
        assert "configured_credentials" in gemini_comp["metadata"]
        assert "primary_model" in gemini_comp["metadata"]
        assert gemini_comp["metadata"]["primary_model"] == "gemini-2.5-flash"
