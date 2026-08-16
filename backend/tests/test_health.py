"""
Tests for Health Endpoint & Honest Status Diagnostics.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_structure(async_client: AsyncClient):
    """Verify that /api/v1/health returns 200 and well-structured component health status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["application"] == "HEALTHY"
    assert data["version"] == "2.0.0"
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))

    # Verify components dictionary
    components = data["components"]
    assert "database" in components
    assert "redis" in components
    assert "youtube" in components
    assert "gemini" in components

    # By default without environment variables set, unconfigured components must report NOT_CONFIGURED
    assert components["database"]["status"] in ["NOT_CONFIGURED", "HEALTHY"]
    assert components["redis"]["status"] in ["NOT_CONFIGURED", "HEALTHY"]


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify that / returns 200 and welcome metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["health"] == "/api/v1/health"
