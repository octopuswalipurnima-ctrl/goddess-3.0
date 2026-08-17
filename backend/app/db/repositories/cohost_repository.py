"""
Co-Host Configuration & Audit Repository for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.cohost import CoHostAuditRecordModel, CoHostConfigModel
from app.db.repositories.base import BaseRepository


class CoHostRepository(BaseRepository[CoHostConfigModel]):
    """Repository managing Co-Host persistent configuration and response audit logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(CoHostConfigModel, session)

    # --- Co-Host Stream Config ---

    async def get_config(self, stream_id: str) -> Optional[CoHostConfigModel]:
        """Fetch Co-Host configuration for a stream."""
        query = select(CoHostConfigModel).where(CoHostConfigModel.stream_id == stream_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_config(
        self,
        stream_id: str,
        enabled: bool = True,
        dry_run: bool = False,
        emergency_stop: bool = False,
        personality_name: str = "goddess",
        cooldown_seconds: float = 5.0,
        config_data: Optional[Dict[str, Any]] = None,
    ) -> CoHostConfigModel:
        """Create or update persistent stream Co-Host configuration."""
        cfg = await self.get_config(stream_id)
        if cfg is None:
            cfg = CoHostConfigModel(
                stream_id=stream_id,
                enabled=enabled,
                dry_run=dry_run,
                emergency_stop=emergency_stop,
                personality_name=personality_name,
                cooldown_seconds=cooldown_seconds,
                config_data=config_data or {},
            )
            self.session.add(cfg)
        else:
            cfg.enabled = enabled
            cfg.dry_run = dry_run
            cfg.emergency_stop = emergency_stop
            cfg.personality_name = personality_name
            cfg.cooldown_seconds = cooldown_seconds
            if config_data is not None:
                cfg.config_data = config_data
            cfg.updated_at = utc_now()
        await self.session.flush()
        return cfg

    # --- Co-Host Audit Records ---

    async def get_audit_by_idempotency_key(self, idempotency_key: str) -> Optional[CoHostAuditRecordModel]:
        """Fetch Co-Host audit record by idempotency key."""
        query = select(CoHostAuditRecordModel).where(
            CoHostAuditRecordModel.idempotency_key == idempotency_key
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def record_audit(
        self,
        stream_id: str,
        message_id: str,
        author_id: str,
        author_name: str,
        intent: str,
        intent_confidence: float,
        response_text: str,
        status: str,
        is_dry_run: bool,
        idempotency_key: str,
        timestamp: Optional[datetime] = None,
    ) -> CoHostAuditRecordModel:
        """
        Record a Co-Host response generation.
        Idempotent: If idempotency_key exists, returns the existing record.
        """
        existing = await self.get_audit_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        record = CoHostAuditRecordModel(
            stream_id=stream_id,
            message_id=message_id,
            author_id=author_id,
            author_name=author_name,
            intent=intent,
            intent_confidence=intent_confidence,
            response_text=response_text,
            status=status,
            is_dry_run=is_dry_run,
            idempotency_key=idempotency_key,
            timestamp=timestamp or utc_now(),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_audits_for_stream(
        self,
        stream_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CoHostAuditRecordModel]:
        """Bounded list of recent Co-Host audit logs for a stream."""
        safe_limit = min(max(1, limit), 500)
        query = (
            select(CoHostAuditRecordModel)
            .where(CoHostAuditRecordModel.stream_id == stream_id)
            .order_by(CoHostAuditRecordModel.timestamp.desc())
            .limit(safe_limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_audits_older_than(self, cutoff: datetime, batch_size: int = 500) -> int:
        """Bounded batch deletion of expired Co-Host audit records."""
        id_query = (
            select(CoHostAuditRecordModel.id)
            .where(CoHostAuditRecordModel.timestamp < cutoff)
            .limit(batch_size)
        )
        id_result = await self.session.execute(id_query)
        target_ids = list(id_result.scalars().all())

        if not target_ids:
            return 0

        del_query = delete(CoHostAuditRecordModel).where(
            CoHostAuditRecordModel.id.in_(target_ids)
        )
        del_result = await self.session.execute(del_query)
        await self.session.flush()
        return del_result.rowcount
