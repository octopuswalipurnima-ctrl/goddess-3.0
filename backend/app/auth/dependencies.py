"""
FastAPI Authentication & Authorization Dependencies for GODDESS AI 2.0.
"""

from typing import Callable, List, Optional
from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import (
    CredentialsException,
    PermissionDeniedException,
    UserInactiveException,
)
from app.auth.models import Permission, UserRole, UserSchema
from app.auth.permissions import get_permissions_for_role, has_permission
from app.auth.service import auth_service
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db

logger = get_logger("auth.dependencies")

# HTTP Bearer Scheme (auto_error=False so we can handle custom error messaging and dev bypass)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    authorization: Optional[str] = Header(default=None),
) -> UserSchema:
    """
    Validate incoming Bearer token and return authenticated UserSchema.
    Supports explicit dev bypass ONLY when explicitly enabled via settings.
    """
    # 1. Check explicit local-dev bypass
    if settings.auth_dev_bypass:
        logger.debug("Operating in explicit local development authentication bypass mode.")
        return UserSchema(
            id=1,
            username="dev_owner",
            email="dev@goddess.local",
            role=UserRole.OWNER,
            is_active=True,
            permissions=get_permissions_for_role(UserRole.OWNER),
        )

    # 2. Extract token from HTTPBearer credentials or Authorization header
    token: Optional[str] = None
    if auth_creds and auth_creds.credentials:
        token = auth_creds.credentials
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        # Check query param (e.g. for WebSockets or specialized download streams)
        token = request.query_params.get("token")

    if not token:
        raise CredentialsException(detail="Authentication token required. Header 'Authorization: Bearer <token>' missing.")

    # 3. Decode & Verify Token
    payload = auth_service.decode_access_token(token)

    try:
        user_role = UserRole(payload.role)
    except ValueError:
        user_role = UserRole.VIEWER

    # 4. Construct effective user schema
    user = UserSchema(
        id=1,  # Sub is username or id
        username=payload.sub,
        role=user_role,
        is_active=True,
        permissions=payload.permissions or get_permissions_for_role(user_role),
    )

    # Attach to request state for access in logging/telemetry
    request.state.user = user
    return user


def require_permission(required_permission: str) -> Callable:
    """
    Dependency factory: Enforce that the authenticated user possesses the specific permission.
    """
    async def permission_checker(
        current_user: UserSchema = Depends(get_current_user),
    ) -> UserSchema:
        if not current_user.is_active:
            raise UserInactiveException()

        if required_permission not in current_user.permissions:
            logger.warning(
                f"Access denied for user '{current_user.username}' (role: {current_user.role.value}): "
                f"missing required permission '{required_permission}'"
            )
            raise PermissionDeniedException(required_permission=required_permission)

        return current_user

    return permission_checker


def require_role(min_role: UserRole) -> Callable:
    """
    Dependency factory: Enforce minimum role in hierarchy (OWNER > ADMIN > OPERATOR > VIEWER).
    """
    hierarchy = {
        UserRole.OWNER: 4,
        UserRole.ADMIN: 3,
        UserRole.OPERATOR: 2,
        UserRole.VIEWER: 1,
    }

    min_weight = hierarchy.get(min_role, 1)

    async def role_checker(
        current_user: UserSchema = Depends(get_current_user),
    ) -> UserSchema:
        if not current_user.is_active:
            raise UserInactiveException()

        user_weight = hierarchy.get(current_user.role, 0)
        if user_weight < min_weight:
            logger.warning(
                f"Access denied for user '{current_user.username}': role '{current_user.role.value}' "
                f"is below required role '{min_role.value}'"
            )
            raise PermissionDeniedException(detail=f"Operation requires minimum role of '{min_role.value}'")

        return current_user

    return role_checker


# Convenient Pre-configured Role Dependencies
require_owner = require_role(UserRole.OWNER)
require_admin = require_role(UserRole.ADMIN)
require_operator = require_role(UserRole.OPERATOR)
require_viewer = require_role(UserRole.VIEWER)
