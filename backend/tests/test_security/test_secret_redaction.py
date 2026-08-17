"""
Tests verifying zero raw credential exposure in logs and API diagnostics.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_health_and_dashboard_zero_secret_leakage(monkeypatch):
    """Verify health and dashboard responses never contain API keys or auth tokens."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health endpoint
        r_health = await client.get("/api/v1/health")
        health_text = r_health.text
        assert "AIzaSy" not in health_text
        assert "Bearer" not in health_text
        assert "secret_key" not in health_text

        # 2. Dashboard overview
        r_dash = await client.get("/api/v1/dashboard/overview")
        dash_text = r_dash.text
        assert "AIzaSy" not in dash_text
        assert "password" not in dash_text
        assert settings.secret_key not in dash_text
