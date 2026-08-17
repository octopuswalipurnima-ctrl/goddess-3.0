"""
Tests for Co-Host REST API Endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_and_update_cohost_config():
    """Verify GET and PUT /api/v1/cohost/config/{stream_id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get default config
        res_get = await client.get("/api/v1/cohost/config/stream_api_test")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["enabled"] is False
        assert data["dry_run"] is True

        # Update config
        res_put = await client.put(
            "/api/v1/cohost/config/stream_api_test",
            json={
                "enabled": True,
                "dry_run": True,
                "personality": {"name": "Astra", "tone": "witty"},
            },
        )
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["enabled"] is True
        assert updated["personality"]["name"] == "Astra"


@pytest.mark.asyncio
async def test_health_endpoint_cohost_diagnostics():
    """Verify GET /api/v1/health includes Co-Host subsystem diagnostics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        health = res.json()
        assert "cohost" in health["components"]
        cohost_status = health["components"]["cohost"]
        assert cohost_status["status"] == "HEALTHY"
        assert "messages_analyzed" in cohost_status["metadata"]
