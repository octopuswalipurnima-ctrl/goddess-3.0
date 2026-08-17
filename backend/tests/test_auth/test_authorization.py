"""
Tests for RBAC Role Hierarchy and Permissions Mapping.
"""

from app.auth.models import Permission, UserRole
from app.auth.permissions import get_permissions_for_role, has_permission


def test_owner_has_all_permissions():
    """Verify OWNER role possesses every platform permission."""
    owner_perms = get_permissions_for_role(UserRole.OWNER)
    all_perms = [p.value for p in Permission]

    assert len(owner_perms) == len(all_perms)
    for p in all_perms:
        assert has_permission(UserRole.OWNER, p) is True


def test_admin_permissions():
    """Verify ADMIN role has operational control but not system.admin."""
    assert has_permission(UserRole.ADMIN, Permission.DASHBOARD_WRITE.value) is True
    assert has_permission(UserRole.ADMIN, Permission.MODERATION_EMERGENCY.value) is True
    assert has_permission(UserRole.ADMIN, Permission.SYSTEM_ADMIN.value) is False


def test_operator_permissions():
    """Verify OPERATOR role cannot execute emergency controls or system admin."""
    assert has_permission(UserRole.OPERATOR, Permission.STREAM_CONTROL.value) is True
    assert has_permission(UserRole.OPERATOR, Permission.MODERATION_CONFIGURE.value) is True
    assert has_permission(UserRole.OPERATOR, Permission.MODERATION_EMERGENCY.value) is False
    assert has_permission(UserRole.OPERATOR, Permission.SYSTEM_ADMIN.value) is False


def test_viewer_permissions():
    """Verify VIEWER role is strictly read-only."""
    assert has_permission(UserRole.VIEWER, Permission.DASHBOARD_READ.value) is True
    assert has_permission(UserRole.VIEWER, Permission.STREAM_READ.value) is True
    assert has_permission(UserRole.VIEWER, Permission.STREAM_CONTROL.value) is False
    assert has_permission(UserRole.VIEWER, Permission.MODERATION_CONFIGURE.value) is False
    assert has_permission(UserRole.VIEWER, Permission.COHOST_CONFIGURE.value) is False
