"""
Authentication API Endpoints for GODDESS AI 2.0.

Provides login, token issuance, session verification, user profile, and user management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_owner
from app.auth.exceptions import CredentialsException, UserInactiveException
from app.auth.models import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserRole,
    UserSchema,
)
from app.auth.permissions import get_permissions_for_role
from app.auth.service import auth_service
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import auth_rate_limit
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db

logger = get_logger("api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(auth_rate_limit)],
    summary="Creator & Operator Login",
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate creator or operator credentials and issue a signed JWT access token.
    Rate limited to prevent brute force.
    """
    username = req.username.strip()
    user_repo = UserRepository(db)

    # 1. Search persistent user in DB
    user = await user_repo.get_by_username(username)

    # 2. Check bootstrap creator if DB is empty or user is bootstrap user
    if user is None and username.lower() == settings.bootstrap_owner_username.lower():
        # Check against bootstrap password from env
        bootstrap_pwd = settings.bootstrap_owner_password or "goddess_creator_2026"
        if req.password == bootstrap_pwd:
            # Bootstrap owner authenticated
            role = UserRole.OWNER
            token = auth_service.create_access_token(
                subject=username,
                role=role,
            )
            return LoginResponse(
                access_token=token,
                token_type="bearer",
                expires_in_seconds=settings.access_token_expire_minutes * 60,
                user=UserSchema(
                    id=1,
                    username=username,
                    email=settings.bootstrap_owner_email,
                    role=role,
                    is_active=True,
                    permissions=get_permissions_for_role(role),
                ),
            )

    if user is None:
        logger.warning(f"Login failed: user '{username}' not found.")
        raise CredentialsException(detail="Invalid username or password.")

    # 3. Verify Password
    if not auth_service.verify_password(req.password, user.hashed_password):
        logger.warning(f"Login failed: invalid password for user '{username}'.")
        raise CredentialsException(detail="Invalid username or password.")

    if not user.is_active:
        raise UserInactiveException()

    # 4. Update last login
    await user_repo.update_last_login(user.id)
    await db.commit()

    role = UserRole(user.role)
    token = auth_service.create_access_token(
        subject=user.username,
        role=role,
    )

    logger.info(f"User '{user.username}' successfully logged in with role '{role.value}'.")
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        user=UserSchema(
            id=user.id,
            username=user.username,
            email=user.email,
            role=role,
            is_active=user.is_active,
            permissions=get_permissions_for_role(role),
        ),
    )


@router.post(
    "/logout",
    summary="Creator Logout",
)
async def logout(
    current_user: UserSchema = Depends(get_current_user),
):
    """
    Log out the current user and invalidate the session.
    """
    logger.info(f"User '{current_user.username}' logged out.")
    return {"message": "Successfully logged out", "status": "ok"}


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Get Current User Profile",
)
async def get_me(
    current_user: UserSchema = Depends(get_current_user),
):
    """
    Retrieve authenticated user profile, role, and active permissions.
    """
    return current_user


@router.post(
    "/users",
    response_model=UserSchema,
    dependencies=[Depends(require_admin)],
    summary="Create User (Admin/Owner Only)",
)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user),
):
    """
    Register a new platform user with specified role (Admin/Owner only).
    """
    user_repo = UserRepository(db)
    existing = await user_repo.get_by_username(req.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered.")

    hashed_pw = auth_service.hash_password(req.password)
    new_user = await user_repo.create_user(
        username=req.username,
        hashed_password=hashed_pw,
        role=req.role,
        email=req.email,
        is_active=req.is_active,
    )
    await db.commit()

    logger.info(f"Admin '{current_user.username}' created new user '{new_user.username}' (role: {new_user.role}).")
    return UserSchema(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=UserRole(new_user.role),
        is_active=new_user.is_active,
        permissions=get_permissions_for_role(UserRole(new_user.role)),
    )
