"""
Tests for Dependency Readiness Probe (/api/v1/health/ready).
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_ready_healthy():
    """Verify readiness probe returns READY when dependencies are functional."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["READY", "READY_DEGRADED"]


@pytest.mark.asyncio
async def test_health_ready_unhealthy_db():
    """Verify readiness probe returns 503 NOT_READY when database is down."""
    mock_db_health = {
        "status": "UNAVAILABLE",
        "details": "Connection refused",
        "latency_ms": None,
    }

    with patch("app.api.v1.endpoints.health.ping_database", AsyncMock(return_value=mock_db_health)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "NOT_READY"
            assert "database_status" in data
