"""
Module Configuration Repository for GODDESS AI 2.0.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.module import ModuleConfigModel
from app.db.repositories.base import BaseRepository


class ModuleRepository(BaseRepository[ModuleConfigModel]):
    """Repository managing persistent stream-specific module configurations."""

    def __init__(self, session: AsyncSession):
        super().__init__(ModuleConfigModel, session)

    async def get_config(self, module_id: str, stream_id: str) -> Optional[ModuleConfigModel]:
        """Fetch module configuration for a specific stream."""
        query = select(ModuleConfigModel).where(
            ModuleConfigModel.module_id == module_id,
            ModuleConfigModel.stream_id == stream_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_config(
        self,
        module_id: str,
        stream_id: str,
        enabled: bool,
        config_data: Dict[str, Any],
    ) -> ModuleConfigModel:
        """Create or update persistent module configuration for a stream."""
        cfg = await self.get_config(module_id, stream_id)
        if cfg is None:
            cfg = ModuleConfigModel(
                module_id=module_id,
                stream_id=stream_id,
                enabled=enabled,
                config_data=config_data,
            )
            self.session.add(cfg)
        else:
            cfg.enabled = enabled
            cfg.config_data = config_data
            cfg.updated_at = utc_now()
        await self.session.flush()
        return cfg

    async def list_configs_for_stream(self, stream_id: str) -> List[ModuleConfigModel]:
        """List all module configurations assigned to a stream."""
        query = select(ModuleConfigModel).where(ModuleConfigModel.stream_id == stream_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all_active_configs(self) -> List[ModuleConfigModel]:
        """List all enabled module configurations across streams."""
        query = select(ModuleConfigModel).where(ModuleConfigModel.enabled.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())
