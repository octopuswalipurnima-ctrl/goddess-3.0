"""
Tests for Moderation REST API Endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_and_update_moderation_config():
    """Verify GET and PUT /api/v1/moderation/config/{stream_id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get default config
        res_get = await client.get("/api/v1/moderation/config/stream_100")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["enabled"] is True
        assert data["kill_switch"] is False

        # Update config (enable emergency kill switch)
        res_put = await client.put(
            "/api/v1/moderation/config/stream_100",
            json={"kill_switch": True, "safe_mode": True},
        )
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["kill_switch"] is True
        assert updated["safe_mode"] is True


@pytest.mark.asyncio
async def test_moderation_dry_run_test_endpoint():
    """Verify POST /api/v1/moderation/test dry-run endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "stream_id": "stream_test_api",
            "author_id": "spammer_api",
            "author_name": "API_Spammer",
            "message_text": "Join our free rewards group: http://phish-claim.xyz/free",
        }
        res = await client.post("/api/v1/moderation/test", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "MALICIOUS_LINK"
        assert data["recommended_action"] == "DELETE"


@pytest.mark.asyncio
async def test_health_endpoint_moderation_diagnostics():
    """Verify GET /api/v1/health includes moderation subsystem metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        health = res.json()
        assert "moderation" in health["components"]
        mod = health["components"]["moderation"]
        assert mod["status"] == "HEALTHY"
        assert "messages_analyzed" in mod["metadata"]
