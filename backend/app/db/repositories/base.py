"""
Generic Base Repository for GODDESS AI 2.0.

Provides standard asynchronous CRUD operations, bounded queries, and transaction safety.
"""

from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Abstract Base Repository with async session."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, record_id: int) -> Optional[ModelType]:
        """Fetch single record by its primary key ID."""
        return await self.session.get(self.model, record_id)

    async def create(self, **kwargs: Any) -> ModelType:
        """Create and add a new model instance."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Bounded list of all model records."""
        safe_limit = min(max(1, limit), 500)
        query = select(self.model).limit(safe_limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total rows in the table."""
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_by_id(self, record_id: int) -> bool:
        """Delete single record by primary key."""
        query = delete(self.model).where(self.model.id == record_id)  # type: ignore
        result = await self.session.execute(query)
        return result.rowcount > 0
