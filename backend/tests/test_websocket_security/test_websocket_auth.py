"""
Tests for WebSocket Handshake Authentication and Token Verification.
"""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.auth.models import UserRole
from app.auth.service import auth_service
from app.main import app


def test_websocket_valid_token_query_param(monkeypatch):
    """Verify WebSocket connection succeeds with a valid JWT token query param."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    token = auth_service.create_access_token("creator_ws", UserRole.OWNER)

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "CONNECTION_ESTABLISHED"
        assert data["user"] == "creator_ws"

        # Test ping-pong
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp["type"] == "PONG"


def test_websocket_invalid_token_rejected(monkeypatch):
    """Verify WebSocket connection is closed when an invalid token is provided."""
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", False)
    monkeypatch.setattr("app.core.config.settings.auth_enabled", True)

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws?token=invalid.tampered.token") as ws:
            ws.receive_json()
    assert exc_info.value.code == 1008
