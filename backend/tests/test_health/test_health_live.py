"""
Tests for Process Liveness Probe (/api/v1/health/live).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_live_endpoint():
    """Verify liveness endpoint returns LIVE status and uptime."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "LIVE"
        assert data["app"] == "Goddess AI 2.0"
        assert "uptime_seconds" in data
