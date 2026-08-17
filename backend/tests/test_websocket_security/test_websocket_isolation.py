"""
Tests for WebSocket Stream Isolation and Subscription Filtering.
"""

import pytest
from starlette.testclient import TestClient
from app.api.v1.endpoints.ws import ws_manager
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.main import app


@pytest.mark.asyncio
async def test_websocket_stream_subscription_filtering(monkeypatch):
    """Verify client only receives events for subscribed streams when specified."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    token = auth_service.create_access_token("creator_iso", UserRole.OWNER)

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        # Handshake
        init_data = ws.receive_json()
        assert init_data["type"] == "CONNECTION_ESTABLISHED"

        # Subscribe to stream_alpha only
        ws.send_text('{"type": "SUBSCRIBE_STREAM", "stream_id": "stream_alpha"}')
        conf = ws.receive_json()
        assert conf["type"] == "SUBSCRIPTION_CONFIRMED"
        assert conf["stream_id"] == "stream_alpha"

        # Broadcast for stream_alpha -> Should receive
        await ws_manager.broadcast_json({"type": "CHAT", "stream_id": "stream_alpha"}, stream_id="stream_alpha")
        msg1 = ws.receive_json()
        assert msg1["stream_id"] == "stream_alpha"
