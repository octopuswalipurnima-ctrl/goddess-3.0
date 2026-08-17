"""
Tests for RBAC Security on AI Controls in GODDESS AI 2.0.
"""

from app.auth.models import Permission, UserRole, UserSchema
from app.auth.permissions import has_permission


def test_rbac_ai_configuration_permissions():
    """Verify ONLY ADMIN and OPERATOR have AI management permissions, while VIEWER is denied."""
    admin_user = UserSchema(id=1, username="admin", role=UserRole.ADMIN, is_active=True)
    operator_user = UserSchema(id=2, username="operator", role=UserRole.OPERATOR, is_active=True)
    viewer_user = UserSchema(id=3, username="viewer", role=UserRole.VIEWER, is_active=True)

    # Admin and Operator can configure AI and invoke emergency controls
    assert has_permission(admin_user.role, Permission.COHOST_CONFIGURE) is True
    assert has_permission(admin_user.role, Permission.MODERATION_EMERGENCY) is True

    assert has_permission(operator_user.role, Permission.COHOST_CONFIGURE) is True
    assert has_permission(operator_user.role, Permission.MODERATION_EMERGENCY) is False  # Admin/Owner only

    # Viewer CANNOT configure Co-Host or invoke emergency controls
    assert has_permission(viewer_user.role, Permission.COHOST_CONFIGURE) is False
    assert has_permission(viewer_user.role, Permission.MODERATION_EMERGENCY) is False
