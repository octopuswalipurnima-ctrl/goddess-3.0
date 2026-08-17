"""
Tests for Module REST API endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_modules_rest_api_lifecycle_and_config():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. List modules
        res = await client.get("/api/v1/modules")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4
        ids = [m["metadata"]["id"] for m in data]
        assert "commands" in ids
        assert "welcome" in ids
        assert "stream_stats" in ids
        assert "viewer_interaction" in ids

        # 2. Get details of 'commands'
        res = await client.get("/api/v1/modules/commands")
        assert res.status_code == 200
        details = res.json()
        assert details["metadata"]["id"] == "commands"

        # 3. Get health of 'commands'
        res = await client.get("/api/v1/modules/commands/health")
        assert res.status_code == 200
        health = res.json()
        assert health["status"] in ["HEALTHY", "DISABLED"]

        # 4. Update stream configuration
        res = await client.put(
            "/api/v1/modules/commands/config/stream_alpha",
            json={"enabled": True, "settings": {"command_cooldown_sec": 3.0}},
        )
        assert res.status_code == 200
        cfg = res.json()
        assert cfg["enabled"] is True
        assert cfg["settings"]["command_cooldown_sec"] == 3.0

        # 5. Retrieve stream configuration
        res = await client.get("/api/v1/modules/commands/config/stream_alpha")
        assert res.status_code == 200
        assert res.json()["enabled"] is True

        # 6. Non-existent module returns 404
        res = await client.get("/api/v1/modules/non_existent_module_xyz")
        assert res.status_code == 404
