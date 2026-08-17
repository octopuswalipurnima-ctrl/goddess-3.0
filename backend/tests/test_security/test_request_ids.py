"""
Tests for X-Request-ID Generation and Propagation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_generated_request_id():
    """Verify responses contain an auto-generated X-Request-ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert req_id.startswith("req_")


@pytest.mark.asyncio
async def test_propagated_custom_request_id():
    """Verify incoming X-Request-ID is propagated in response headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/",
            headers={"X-Request-ID": "custom-trace-uuid-12345"},
        )
        assert response.headers.get("X-Request-ID") == "custom-trace-uuid-12345"
