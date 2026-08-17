"""
Tests for Railway Deployment Configuration and Health Endpoints in GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.main import app


@pytest.mark.asyncio
async def test_deployment_health_endpoints_available():
    """Verify standard liveness and readiness endpoints exist."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_live = await client.get("/api/v1/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] in ["LIVE", "ALIVE"]

        res_ready = await client.get("/api/v1/health/ready")
        assert res_ready.status_code in [200, 503]
