"""
Tests for Health Diagnostic Probes in GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.main import app


@pytest.mark.asyncio
async def test_health_live_ready_and_detailed_endpoints():
    """Verify /health/live, /health/ready, and /health/detailed probes return 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Live probe
        r_live = await client.get("/api/v1/health/live")
        assert r_live.status_code == 200
        assert r_live.json()["status"] == "LIVE"

        # 2. Ready probe
        r_ready = await client.get("/api/v1/health/ready")
        assert r_ready.status_code == 200
        assert r_ready.json()["status"] == "READY"

        # 3. Detailed probe
        r_det = await client.get("/api/v1/health/detailed")
        assert r_det.status_code == 200
        data = r_det.json()
        assert "overall_status" in data
        assert "infrastructure" in data
