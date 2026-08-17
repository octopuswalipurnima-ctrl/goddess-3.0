"""
Unit tests for Dashboard Aggregator API endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_dashboard_overview():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get("/api/v1/dashboard/overview")
        assert res.status_code == 200
        data = res.json()

        # Check required fields
        assert "timestamp" in data
        assert "version" in data
        assert "streams" in data
        assert "moderation_metrics" in data
        assert "cohost_metrics" in data
        assert "modules_summary" in data
        assert "ai_diagnostics" in data
        assert "youtube_diagnostics" in data

        # Check safe diagnostic counts
        assert "configured_keys" in data["ai_diagnostics"]
        assert "primary_model" in data["ai_diagnostics"]
        assert "registered_count" in data["modules_summary"]
        assert data["modules_summary"]["registered_count"] >= 4
