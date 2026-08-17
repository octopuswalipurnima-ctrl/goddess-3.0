"""
User Persistent Repository for GODDESS AI 2.0.
"""

from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserRole
from app.db.base import utc_now
from app.db.models.user import UserModel
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository managing persistent user authentication records."""

    def __init__(self, session: AsyncSession):
        super().__init__(UserModel, session)

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """Fetch user by username (case-insensitive search)."""
        query = select(UserModel).where(func.lower(UserModel.username) == username.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Fetch user by email (case-insensitive)."""
        query = select(UserModel).where(func.lower(UserModel.email) == email.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        username: str,
        hashed_password: str,
        role: UserRole = UserRole.OPERATOR,
        email: Optional[str] = None,
        is_active: bool = True,
    ) -> UserModel:
        """Create and persist a new user."""
        user = UserModel(
            username=username,
            hashed_password=hashed_password,
            role=role.value if isinstance(role, UserRole) else role,
            email=email,
            is_active=is_active,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_login(self, user_id: int) -> None:
        """Update last login timestamp for user."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = utc_now()
            user.updated_at = utc_now()
            await self.session.flush()

    async def count_users(self) -> int:
        """Count total registered users."""
        query = select(func.count(UserModel.id))
        result = await self.session.execute(query)
        return int(result.scalar() or 0)
