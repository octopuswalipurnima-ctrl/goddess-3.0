"""
Stream & Stream Configuration Repository for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.stream import StreamConfigModel, StreamModel
from app.db.repositories.base import BaseRepository


class StreamRepository(BaseRepository[StreamModel]):
    """Repository managing persistent stream states and configurations."""

    def __init__(self, session: AsyncSession):
        super().__init__(StreamModel, session)

    async def get_by_stream_id(self, stream_id: str) -> Optional[StreamModel]:
        """Fetch stream record by its stream_id."""
        query = select(StreamModel).where(StreamModel.stream_id == stream_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_or_update_stream(
        self,
        stream_id: str,
        channel_id: Optional[str] = None,
        title: Optional[str] = None,
        status: str = "INITIALIZING",
        started_at: Optional[datetime] = None,
    ) -> StreamModel:
        """Create a new stream record or update an existing one."""
        stream = await self.get_by_stream_id(stream_id)
        if stream is None:
            stream = StreamModel(
                stream_id=stream_id,
                channel_id=channel_id,
                title=title,
                status=status,
                started_at=started_at or utc_now(),
            )
            self.session.add(stream)
        else:
            if channel_id is not None:
                stream.channel_id = channel_id
            if title is not None:
                stream.title = title
            stream.status = status
            if started_at is not None:
                stream.started_at = started_at
            stream.updated_at = utc_now()
        await self.session.flush()
        return stream

    async def update_status(
        self,
        stream_id: str,
        status: str,
        ended_at: Optional[datetime] = None,
    ) -> Optional[StreamModel]:
        """Update stream lifecycle status (e.g., ACTIVE, STOPPED, FAILED)."""
        stream = await self.get_by_stream_id(stream_id)
        if stream:
            stream.status = status
            if ended_at:
                stream.ended_at = ended_at
            stream.updated_at = utc_now()
            await self.session.flush()
        return stream

    async def list_active_streams(self) -> List[StreamModel]:
        """List all currently active stream records."""
        query = select(StreamModel).where(StreamModel.status.in_(["ACTIVE", "RUNNING", "INITIALIZING"]))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # --- Stream Configuration Methods ---

    async def get_config(self, stream_id: str) -> Optional[StreamConfigModel]:
        """Get stream configuration record."""
        query = select(StreamConfigModel).where(StreamConfigModel.stream_id == stream_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_config(
        self,
        stream_id: str,
        config_data: Dict[str, Any],
        enabled: bool = True,
    ) -> StreamConfigModel:
        """Create or update persistent stream configuration."""
        cfg = await self.get_config(stream_id)
        if cfg is None:
            cfg = StreamConfigModel(
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
