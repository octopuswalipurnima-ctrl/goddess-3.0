"""
Tests for Dashboard Operations Endpoints in GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.main import app


@pytest.mark.asyncio
async def test_dashboard_operations_overview_and_streams_endpoints():
    """Verify operations overview and streams endpoints return expected schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default dev bypass or valid token
        token = AuthService.create_access_token(subject="admin", role=UserRole.ADMIN)
        headers = {"Authorization": f"Bearer {token}"}

        res_ov = await client.get("/api/v1/operations/overview", headers=headers)
        assert res_ov.status_code == 200
        data_ov = res_ov.json()
        assert "system_status" in data_ov

        res_str = await client.get("/api/v1/operations/streams", headers=headers)
        assert res_str.status_code == 200
        data_str = res_str.json()
        assert "STREAM_A" in data_str
