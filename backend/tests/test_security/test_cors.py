"""
Tests for Production CORS Configuration.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin():
    """Verify CORS preflight succeeds for configured frontend origin."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_disallowed_origin():
    """Verify CORS does not reflect unauthorized origins."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health",
            headers={
                "Origin": "http://malicious-attacker-site.com",
            },
        )
        # Should not grant access to disallowed origin
        assert response.headers.get("access-control-allow-origin") != "http://malicious-attacker-site.com"
