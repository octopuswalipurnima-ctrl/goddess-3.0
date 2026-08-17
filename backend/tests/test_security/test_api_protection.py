"""
Tests verifying that all protected endpoints enforce authentication and RBAC.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.main import app


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(monkeypatch):
    """Verify unauthenticated requests to protected endpoints return HTTP 401."""
    # Ensure dev bypass is off for security testing
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Dashboard
        r1 = await client.get("/api/v1/dashboard/overview")
        assert r1.status_code == 401

        # Streams
        r2 = await client.get("/api/v1/streams")
        assert r2.status_code == 401

        # Moderation
        r3 = await client.get("/api/v1/moderation/stats")
        assert r3.status_code == 401

        # Co-Host
        r4 = await client.get("/api/v1/cohost/stats")
        assert r4.status_code == 401

        # Modules
        r5 = await client.get("/api/v1/modules")
        assert r5.status_code == 401


@pytest.mark.asyncio
async def test_viewer_forbidden_from_destructive_actions(monkeypatch):
    """Verify VIEWER role can read dashboard but cannot execute control actions (HTTP 403)."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    viewer_token = auth_service.create_access_token(
        subject="viewer_user",
        role=UserRole.VIEWER,
    )
    headers = {"Authorization": f"Bearer {viewer_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Allowed to read dashboard
        r1 = await client.get("/api/v1/dashboard/overview", headers=headers)
        assert r1.status_code == 200

        # Forbidden from creating streams
        r2 = await client.post("/api/v1/streams", json={"stream_id": "s1"}, headers=headers)
        assert r2.status_code == 403

        # Forbidden from stopping streams
        r3 = await client.post("/api/v1/streams/s1/stop", headers=headers)
        assert r3.status_code == 403

        # Forbidden from enabling modules
        r4 = await client.post("/api/v1/modules/commands/enable", headers=headers)
        assert r4.status_code == 403
