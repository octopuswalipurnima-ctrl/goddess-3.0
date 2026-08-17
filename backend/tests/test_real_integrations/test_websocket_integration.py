"""
Real Service Integration Audit: Authenticated WebSocket Gateway for GODDESS AI 2.0.
"""

import pytest
from app.api.v1.endpoints.ws import HardenedConnectionManager
from app.auth.models import UserRole, UserSchema
from app.auth.permissions import get_permissions_for_role


def test_websocket_authenticated_client_stream_filtering():
    """Verify AuthenticatedClient filters broadcasts strictly according to subscribed streams."""
    user = UserSchema(
        id=1,
        username="streamer_alice",
        role=UserRole.OPERATOR,
        is_active=True,
        permissions=get_permissions_for_role(UserRole.OPERATOR),
    )

    from app.api.v1.endpoints.ws import AuthenticatedClient
    client = AuthenticatedClient(websocket=None, user=user)  # type: ignore

    # Subscribed to STREAM_A only
    client.subscribed_streams.add("STREAM_A")

    assert client.can_receive_stream("STREAM_A") is True
    assert client.can_receive_stream("STREAM_B") is False
    assert client.can_receive_stream(None) is True  # Global events
