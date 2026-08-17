"""
Moderation Audit Repository for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.moderation import ModerationAuditRecordModel
from app.db.repositories.base import BaseRepository


class ModerationRepository(BaseRepository[ModerationAuditRecordModel]):
    """Repository for querying, recording, and retaining 3-tier moderation audit logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(ModerationAuditRecordModel, session)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[ModerationAuditRecordModel]:
        """Fetch audit record by unique idempotency key."""
        query = select(ModerationAuditRecordModel).where(
            ModerationAuditRecordModel.idempotency_key == idempotency_key
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def record_audit(
        self,
        stream_id: str,
        message_id: str,
        author_id: str,
        author_name: str,
        category: str,
        confidence: float,
        severity: str,
        recommended_action: str,
        action_taken: str,
        action_status: str,
        is_dry_run: bool,
        idempotency_key: str,
        reason: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> ModerationAuditRecordModel:
        """
        Record a moderation decision.
        Idempotent: If idempotency_key exists, returns the existing record.
        """
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        record = ModerationAuditRecordModel(
            stream_id=stream_id,
            message_id=message_id,
            author_id=author_id,
            author_name=author_name,
            category=category,
            confidence=confidence,
            severity=severity,
            recommended_action=recommended_action,
            action_taken=action_taken,
            action_status=action_status,
            is_dry_run=is_dry_run,
            reason=reason,
            idempotency_key=idempotency_key,
            timestamp=timestamp or utc_now(),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_audits_for_stream(
        self,
        stream_id: str,
        category: Optional[str] = None,
        action_status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ModerationAuditRecordModel]:
        """Bounded time-range query for stream moderation audit records."""
        safe_limit = min(max(1, limit), 500)
        query = select(ModerationAuditRecordModel).where(
            ModerationAuditRecordModel.stream_id == stream_id
        )

        if category:
            query = query.where(ModerationAuditRecordModel.category == category)
        if action_status:
            query = query.where(ModerationAuditRecordModel.action_status == action_status)
        if since:
            query = query.where(ModerationAuditRecordModel.timestamp >= since)

        query = query.order_by(ModerationAuditRecordModel.timestamp.desc()).limit(safe_limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_audits_for_stream(
        self,
        stream_id: str,
        category: Optional[str] = None,
    ) -> int:
        """Count total audit records for a given stream."""
        query = select(func.count()).select_from(ModerationAuditRecordModel).where(
            ModerationAuditRecordModel.stream_id == stream_id
        )
        if category:
            query = query.where(ModerationAuditRecordModel.category == category)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_older_than(self, cutoff: datetime, batch_size: int = 500) -> int:
        """
        Bounded batch deletion of expired audit records for data retention.
        Returns the number of deleted records.
        """
        # Find IDs of records older than cutoff
        id_query = (
            select(ModerationAuditRecordModel.id)
            .where(ModerationAuditRecordModel.timestamp < cutoff)
            .limit(batch_size)
        )
        id_result = await self.session.execute(id_query)
        target_ids = list(id_result.scalars().all())

        if not target_ids:
            return 0

        del_query = delete(ModerationAuditRecordModel).where(
            ModerationAuditRecordModel.id.in_(target_ids)
        )
        del_result = await self.session.execute(del_query)
        await self.session.flush()
        return del_result.rowcount
