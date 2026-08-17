"""
Tests verifying that emergency controls require explicit authorization.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.main import app


@pytest.mark.asyncio
async def test_emergency_controls_require_moderation_emergency(monkeypatch):
    """Verify that operator lacking moderation.emergency cannot toggle kill switch or safe mode."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    operator_token = auth_service.create_access_token(
        subject="operator_op",
        role=UserRole.OPERATOR,
    )
    headers = {"Authorization": f"Bearer {operator_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Operator trying to toggle emergency kill switch
        response = await client.put(
            "/api/v1/moderation/config/stream_alpha",
            json={"kill_switch": True},
            headers=headers,
        )
        assert response.status_code == 403
        assert "moderation.emergency" in response.text

        # Operator trying to reset circuit breaker
        cb_res = await client.post(
            "/api/v1/moderation/circuit-breaker/reset/stream_alpha",
            headers=headers,
        )
        assert cb_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_allowed_emergency_controls(monkeypatch):
    """Verify that ADMIN role possessing moderation.emergency can toggle kill switch."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    admin_token = auth_service.create_access_token(
        subject="admin_user",
        role=UserRole.ADMIN,
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/moderation/config/stream_alpha",
            json={"kill_switch": True},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["kill_switch"] is True
