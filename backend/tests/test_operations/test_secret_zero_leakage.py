"""
Tests for Zero Secret Leakage across Operations APIs and Diagnostics in GODDESS AI 2.0.
"""

import json
from httpx import ASGITransport, AsyncClient
import pytest
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.main import app


@pytest.mark.asyncio
async def test_operations_api_responses_contain_zero_secrets():
    """Verify operations endpoints never leak raw API keys or passwords."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = AuthService.create_access_token(subject="admin", role=UserRole.ADMIN)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Check detailed health
        r_health = await client.get("/api/v1/health/detailed")
        text_health = json.dumps(r_health.json())
        assert "AIzaSy" not in text_health
        assert "secret_key" not in text_health

        # 2. Check provider operations
        r_prov = await client.get("/api/v1/operations/providers", headers=headers)
        text_prov = json.dumps(r_prov.json())
        assert "AIzaSy" not in text_prov
