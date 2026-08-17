"""
Full End-to-End Creator Workflow Integration Test for GODDESS AI 2.0.
"""

from httpx import ASGITransport, AsyncClient
import pytest
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.core.safety_controller import safety_controller
from app.main import app


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_full_creator_workflow():
    """
    Verify complete creator workflow:
    1. Authenticate as OWNER
    2. Check Operations Overview
    3. Toggle Safe Mode
    4. Enable CoHost Dry-Run
    5. Trigger Stream Emergency Stop
    6. Verify Audit Log
    7. Clear Emergency Stop
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = AuthService.create_access_token(subject="streamer_owner", role=UserRole.OWNER)
        headers = {"Authorization": f"Bearer {owner_token}"}

        # 1. Overview
        r1 = await client.get("/api/v1/operations/overview", headers=headers)
        assert r1.status_code == 200

        # 2. Toggle Safe Mode on STREAM_A
        r2 = await client.post("/api/v1/operations/streams/STREAM_A/safe-mode/enable", headers=headers)
        assert r2.status_code == 200

        # 3. Toggle CoHost dry-run
        r3 = await client.post(
            "/api/v1/operations/streams/STREAM_A/cohost/dry-run",
            json={"dry_run": True},
            headers=headers,
        )
        assert r3.status_code == 200

        # 4. Trigger Emergency Stop on STREAM_A
        r4 = await client.post("/api/v1/operations/streams/STREAM_A/emergency-stop", headers=headers)
        assert r4.status_code == 200

        # 5. Check Audit Log
        r5 = await client.get("/api/v1/operations/audit?stream_id=STREAM_A", headers=headers)
        assert r5.status_code == 200
        logs = r5.json()
        assert len(logs) >= 3

        # 6. Clear Emergency Stop
        r6 = await client.post("/api/v1/operations/emergency-stop/clear", headers=headers)
        assert r6.status_code == 200
