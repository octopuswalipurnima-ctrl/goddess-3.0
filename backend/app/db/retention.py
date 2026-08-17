"""
Audit Retention and Pruning Manager for GODDESS AI 2.0.

Provides bounded batch deletion of historical moderation and Co-Host audit records
older than a configurable retention window (default: 30 days).
Prevents unbounded database growth and never deletes active configurations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.repositories.cohost_repository import CoHostRepository
from app.db.repositories.moderation_repository import ModerationRepository

logger = get_logger("db.retention")


class AuditRetentionManager:
    """Manages periodic bounded cleanup of expired audit records."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mod_repo = ModerationRepository(session)
        self.cohost_repo = CoHostRepository(session)

    async def prune_expired_records(
        self,
        retention_days: Optional[int] = None,
        batch_size: int = 500,
        max_batches: int = 10,
    ) -> Dict[str, Any]:
        """
        Execute bounded batch pruning of expired audit records.
        """
        days = retention_days if retention_days is not None else settings.audit_retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        total_mod_deleted = 0
        total_cohost_deleted = 0

        # Prune Moderation Audits in bounded batches
        for _ in range(max_batches):
            deleted = await self.mod_repo.delete_older_than(cutoff, batch_size=batch_size)
            total_mod_deleted += deleted
            if deleted < batch_size:
                break

        # Prune Co-Host Audits in bounded batches
        for _ in range(max_batches):
            deleted = await self.cohost_repo.delete_audits_older_than(cutoff, batch_size=batch_size)
            total_cohost_deleted += deleted
            if deleted < batch_size:
                break

        if total_mod_deleted > 0 or total_cohost_deleted > 0:
            logger.info(
                f"Audit retention pruning complete: deleted {total_mod_deleted} mod records "
                f"and {total_cohost_deleted} co-host records older than {days} days."
            )

        return {
            "moderation_audits_deleted": total_mod_deleted,
            "cohost_audits_deleted": total_cohost_deleted,
            "retention_days": days,
            "cutoff_timestamp": cutoff.isoformat(),
        }
