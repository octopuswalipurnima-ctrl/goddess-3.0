"""
Role-Based Access Control (RBAC) & Permissions for GODDESS AI 2.0.
"""

from typing import List, Set
from app.auth.models import Permission, UserRole

# Explicit Role-Permission mappings
ROLE_PERMISSIONS = {
    UserRole.OWNER: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.STREAM_READ,
        Permission.STREAM_CONTROL,
        Permission.MODERATION_READ,
        Permission.MODERATION_CONFIGURE,
        Permission.MODERATION_EMERGENCY,
        Permission.COHOST_READ,
        Permission.COHOST_CONFIGURE,
        Permission.MODULES_READ,
        Permission.MODULES_CONFIGURE,
        Permission.PERSISTENCE_READ,
        Permission.SYSTEM_ADMIN,
    },
    UserRole.ADMIN: {
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_WRITE,
        Permission.STREAM_READ,
        Permission.STREAM_CONTROL,
        Permission.MODERATION_READ,
        Permission.MODERATION_CONFIGURE,
        Permission.MODERATION_EMERGENCY,
        Permission.COHOST_READ,
        Permission.COHOST_CONFIGURE,
        Permission.MODULES_READ,
        Permission.MODULES_CONFIGURE,
        Permission.PERSISTENCE_READ,
    },
    UserRole.OPERATOR: {
        Permission.DASHBOARD_READ,
        Permission.STREAM_READ,
        Permission.STREAM_CONTROL,
        Permission.MODERATION_READ,
        Permission.MODERATION_CONFIGURE,
        Permission.COHOST_READ,
        Permission.COHOST_CONFIGURE,
        Permission.MODULES_READ,
    },
    UserRole.VIEWER: {
        Permission.DASHBOARD_READ,
        Permission.STREAM_READ,
        Permission.MODERATION_READ,
        Permission.COHOST_READ,
        Permission.MODULES_READ,
    },
}


def get_permissions_for_role(role: UserRole) -> List[str]:
    """Retrieve all effective string permission tokens for a role."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return sorted([p.value for p in perms])


def has_permission(user_role: UserRole, required_permission: str) -> bool:
    """Check whether a role possesses the specified permission."""
    perms = ROLE_PERMISSIONS.get(user_role, set())
    return any(p.value == required_permission for p in perms)
