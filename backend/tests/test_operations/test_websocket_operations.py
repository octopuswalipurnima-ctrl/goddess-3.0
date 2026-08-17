"""
Tests for WebSocket Operations and Event Subscriptions in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.api.v1.endpoints.ws import HardenedConnectionManager
from app.auth.models import UserRole, UserSchema


@pytest.mark.asyncio
async def test_websocket_broadcasts_operational_events():
    """Verify WebSocket manager relays operational payloads."""
    ws_mgr = HardenedConnectionManager()

    mock_ws = AsyncMock()
    user = UserSchema(id=1, username="operator_1", role=UserRole.OPERATOR, permissions=["stream.read"])

    client = await ws_mgr.register(mock_ws, user)
    assert ws_mgr.active_count == 1

    # Broadcast event
    await ws_mgr.broadcast_json({"type": "OPERATIONAL_EVENT", "data": {"status": "LIVE"}})
    mock_ws.send_json.assert_called_once()
