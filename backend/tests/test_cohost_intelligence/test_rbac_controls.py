"""
Tests for RBAC Protection over Co-Host API Endpoints in GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.main import app


@pytest.mark.asyncio
async def test_cohost_config_update_requires_cohost_configure_permission(monkeypatch):
    """Verify viewer cannot modify Co-Host configuration (requires cohost.configure)."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    viewer_token = AuthService.create_access_token(
        subject="viewer_user",
        role=UserRole.VIEWER,
    )

    headers = {"Authorization": f"Bearer {viewer_token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/cohost/config/STREAM_A",
            json={"enabled": True},
            headers=headers,
        )
        assert response.status_code == 403
