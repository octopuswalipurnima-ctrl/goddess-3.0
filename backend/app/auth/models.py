"""
Authentication & Authorization Data Models for GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """Hierarchical roles for GODDESS AI 2.0 platform."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    """Explicit permission tokens."""
    DASHBOARD_READ = "dashboard.read"
    DASHBOARD_WRITE = "dashboard.write"
    STREAM_READ = "stream.read"
    STREAM_CONTROL = "stream.control"
    STREAM_ATTACH = "stream.attach"
    STREAM_DETACH = "stream.detach"
    STREAM_RECONNECT = "stream.reconnect"
    STREAM_SAFE_MODE = "stream.safe_mode"
    MODERATION_READ = "moderation.read"
    MODERATION_CONFIGURE = "moderation.configure"
    MODERATION_CONTROL = "moderation.control"
    MODERATION_EMERGENCY = "moderation.emergency"
    COHOST_READ = "cohost.read"
    COHOST_CONFIGURE = "cohost.configure"
    COHOST_CONTROL = "cohost.control"
    MODULES_READ = "modules.read"
    MODULES_CONFIGURE = "modules.configure"
    PERSISTENCE_READ = "persistence.read"
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_READ = "system.read"
    SYSTEM_CONTROL = "system.control"
    AI_READ = "ai.read"
    AUDIT_READ = "audit.read"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: Optional[str] = Field(default=None, description="Optional email address")
    role: UserRole = Field(default=UserRole.OPERATOR, description="User role")
    is_active: bool = Field(default=True, description="Account active status")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext password for registration")


class UserSchema(UserBase):
    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    permissions: List[str] = Field(default_factory=list, description="Computed effective permissions")
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(..., description="Creator username")
    password: str = Field(..., description="Creator password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserSchema


class TokenPayload(BaseModel):
    sub: str  # username or user_id
    role: str
    permissions: List[str]
    exp: int
    iat: int
    iss: str
    aud: str
