"""
Tests for WebSocket Real-Time Safety & Supervisor Telemetry in GODDESS AI 2.0.
"""

import pytest
from starlette.testclient import TestClient
from app.api.v1.endpoints.ws import ws_manager
from app.main import app


@pytest.mark.asyncio
async def test_websocket_broadcast_safe_payloads():
    """Verify ws_manager.broadcast_json runs cleanly without error."""
    await ws_manager.broadcast_json({
        "type": "SAFETY_STATE_CHANGED",
        "data": {"stream_id": "STREAM_A", "state": "SAFE_MODE", "reason": "Test"},
    })
    # If no clients connected, should cleanly succeed
    assert ws_manager.active_count == 0
