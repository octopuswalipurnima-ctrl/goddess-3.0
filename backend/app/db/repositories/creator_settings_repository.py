"""
Creator Settings Repository for GODDESS AI 2.0.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.creator_settings import CreatorSettingsModel
from app.db.repositories.base import BaseRepository


class CreatorSettingsRepository(BaseRepository[CreatorSettingsModel]):
    """Repository managing key-value creator preferences and dashboard defaults."""

    def __init__(self, session: AsyncSession):
        super().__init__(CreatorSettingsModel, session)

    async def get_setting(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch setting value dict by its key, returning default if not found."""
        query = select(CreatorSettingsModel).where(CreatorSettingsModel.key == key)
        result = await self.session.execute(query)
        record = result.scalar_one_or_none()
        if record:
            return record.value_data
        return default or {}

    async def set_setting(self, key: str, value_data: Dict[str, Any]) -> CreatorSettingsModel:
        """Create or update a creator setting."""
        query = select(CreatorSettingsModel).where(CreatorSettingsModel.key == key)
        result = await self.session.execute(query)
        record = result.scalar_one_or_none()
        if record is None:
            record = CreatorSettingsModel(
                key=key,
                value_data=value_data,
            )
            self.session.add(record)
        else:
            record.value_data = value_data
            record.updated_at = utc_now()
        await self.session.flush()
        return record

    async def list_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all settings as a key -> value_data dictionary."""
        query = select(CreatorSettingsModel)
        result = await self.session.execute(query)
        return {r.key: r.value_data for r in result.scalars().all()}
