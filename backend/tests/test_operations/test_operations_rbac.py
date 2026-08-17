"""
Tests for Operations Endpoints RBAC Enforcement in GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.main import app


@pytest.mark.asyncio
async def test_viewer_role_cannot_trigger_emergency_stop(monkeypatch):
    """Verify VIEWER role cannot trigger emergency stop (requires moderation.emergency)."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    viewer_token = AuthService.create_access_token(
        subject="viewer_user",
        role=UserRole.VIEWER,
    )

    headers = {"Authorization": f"Bearer {viewer_token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Attempt global emergency stop
        res = await client.post(
            "/api/v1/operations/emergency-stop",
            json={"reason": "Unauthorized halt attempt"},
            headers=headers,
        )
        assert res.status_code == 403

        # 2. Allowed to read overview
        res_read = await client.get("/api/v1/operations/overview", headers=headers)
        assert res_read.status_code == 200
