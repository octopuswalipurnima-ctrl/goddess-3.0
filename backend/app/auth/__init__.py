"""
Authentication & Authorization Package for GODDESS AI 2.0.
"""

from app.auth.models import (
    LoginRequest,
    LoginResponse,
    Permission,
    TokenPayload,
    UserCreate,
    UserRole,
    UserSchema,
)
from app.auth.permissions import get_permissions_for_role, has_permission
from app.auth.service import auth_service
from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_operator,
    require_owner,
    require_permission,
    require_role,
    require_viewer,
)
from app.auth.exceptions import (
    CredentialsException,
    InvalidTokenException,
    PermissionDeniedException,
    RateLimitExceededException,
    TokenExpiredException,
    UserInactiveException,
)
from app.auth.middleware import (
    RequestCorrelationMiddleware,
    SecurityHeadersMiddleware,
)

__all__ = [
    "UserRole",
    "Permission",
    "UserSchema",
    "UserCreate",
    "LoginRequest",
    "LoginResponse",
    "TokenPayload",
    "auth_service",
    "get_permissions_for_role",
    "has_permission",
    "get_current_user",
    "require_permission",
    "require_role",
    "require_owner",
    "require_admin",
    "require_operator",
    "require_viewer",
    "CredentialsException",
    "PermissionDeniedException",
    "TokenExpiredException",
    "InvalidTokenException",
    "UserInactiveException",
    "RateLimitExceededException",
    "RequestCorrelationMiddleware",
    "SecurityHeadersMiddleware",
]
