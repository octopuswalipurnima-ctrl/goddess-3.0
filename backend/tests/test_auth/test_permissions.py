"""
Tests for Permission Enforcement and Dependency Behavior.
"""

from unittest.mock import MagicMock
import pytest
from app.auth.dependencies import require_permission, require_role
from app.auth.exceptions import PermissionDeniedException, UserInactiveException
from app.auth.models import Permission, UserRole, UserSchema
from app.auth.permissions import get_permissions_for_role


@pytest.mark.asyncio
async def test_require_permission_success():
    """Verify require_permission allows user with matching permission."""
    checker = require_permission("stream.control")

    user = UserSchema(
        id=1,
        username="streamer_sam",
        role=UserRole.OPERATOR,
        is_active=True,
        permissions=["stream.read", "stream.control"],
    )

    result = await checker(current_user=user)
    assert result.username == "streamer_sam"


@pytest.mark.asyncio
async def test_require_permission_denied():
    """Verify require_permission raises 403 when user lacks permission."""
    checker = require_permission("moderation.emergency")

    user = UserSchema(
        id=2,
        username="viewer_val",
        role=UserRole.VIEWER,
        is_active=True,
        permissions=["dashboard.read", "stream.read"],
    )

    with pytest.raises(PermissionDeniedException):
        await checker(current_user=user)


@pytest.mark.asyncio
async def test_inactive_user_rejected():
    """Verify inactive user accounts are rejected immediately."""
    checker = require_permission("dashboard.read")

    inactive_user = UserSchema(
        id=3,
        username="inactive_ian",
        role=UserRole.OWNER,
        is_active=False,
        permissions=get_permissions_for_role(UserRole.OWNER),
    )

    with pytest.raises(UserInactiveException):
        await checker(current_user=inactive_user)
