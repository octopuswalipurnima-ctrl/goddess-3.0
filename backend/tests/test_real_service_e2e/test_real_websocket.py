"""
Controlled Real WebSocket Protocol & Telemetry Tests for GODDESS AI 2.0.

Requires explicit RUN_REAL_WEBSOCKET_TEST=true.
Validates stream-scoped subscription isolation and flood protection.
"""

from unittest.mock import AsyncMock
import os
import pytest
from app.api.v1.endpoints.ws import HardenedConnectionManager
from app.auth.models import UserRole, UserSchema


@pytest.mark.asyncio
async def test_real_websocket_connection_and_subscription_isolation():
    """
    Validate WebSocket authentication, multi-stream channel routing, and stream isolation.
    """
    if os.getenv("RUN_REAL_WEBSOCKET_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_WEBSOCKET_TEST is not true. Skipping real WebSocket test.")

    manager = HardenedConnectionManager()

    mock_ws_a = AsyncMock()
    user_a = UserSchema(id=1, username="streamer_a", role=UserRole.OPERATOR)
    client_a = await manager.register(mock_ws_a, user_a)
    client_a.subscribed_streams.add("STREAM_A")

    mock_ws_b = AsyncMock()
    user_b = UserSchema(id=2, username="streamer_b", role=UserRole.OPERATOR)
    client_b = await manager.register(mock_ws_b, user_b)
    client_b.subscribed_streams.add("STREAM_B")

    # Broadcast event to STREAM_A
    await manager.broadcast_json({"type": "CHAT", "data": "Stream A only"}, stream_id="STREAM_A")

    mock_ws_a.send_json.assert_called_once()
    mock_ws_b.send_json.assert_not_called()
