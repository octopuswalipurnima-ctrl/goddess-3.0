"""
Tests for WebSocket Stream Isolation in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.api.v1.endpoints.ws import HardenedConnectionManager
from app.auth.models import UserRole, UserSchema


@pytest.mark.asyncio
async def test_websocket_stream_subscription_isolation():
    """Verify client subscribed to STREAM_A never receives STREAM_B broadcasts."""
    ws_mgr = HardenedConnectionManager()

    ws_a = AsyncMock()
    user_a = UserSchema(id=1, username="user_a", role=UserRole.VIEWER)
    client_a = await ws_mgr.register(ws_a, user_a)
    client_a.subscribed_streams.add("STREAM_A")

    ws_b = AsyncMock()
    user_b = UserSchema(id=2, username="user_b", role=UserRole.VIEWER)
    client_b = await ws_mgr.register(ws_b, user_b)
    client_b.subscribed_streams.add("STREAM_B")

    # Broadcast event scoped to STREAM_A
    await ws_mgr.broadcast_json({"type": "CHAT", "msg": "Hello Stream A"}, stream_id="STREAM_A")

    ws_a.send_json.assert_called_once()
    ws_b.send_json.assert_not_called()
