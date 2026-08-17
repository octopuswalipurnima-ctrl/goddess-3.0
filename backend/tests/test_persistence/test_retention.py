"""
Tests for AuditRetentionManager pruning expired audit logs in bounded batches.
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.db.models.cohost import CoHostAuditRecordModel
from app.db.models.moderation import ModerationAuditRecordModel
from app.db.retention import AuditRetentionManager


@pytest.mark.asyncio
async def test_audit_retention_pruning(test_db_session):
    """Verify pruning removes old audits and keeps recent audits."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=45)
    recent_time = now - timedelta(days=5)

    # 1. Add expired record (> 30 days)
    old_mod = ModerationAuditRecordModel(
        stream_id="stream_alpha",
        message_id="old_msg",
        author_id="user_old",
        author_name="OldUser",
        category="SPAM",
        confidence=0.9,
        severity="LOW",
        recommended_action="DELETE",
        action_taken="DELETE",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="old_mod_key",
        timestamp=old_time,
    )
    test_db_session.add(old_mod)

    # 2. Add recent record (< 30 days)
    recent_mod = ModerationAuditRecordModel(
        stream_id="stream_alpha",
        message_id="recent_msg",
        author_id="user_recent",
        author_name="RecentUser",
        category="SAFE",
        confidence=0.99,
        severity="LOW",
        recommended_action="NONE",
        action_taken="NONE",
        action_status="APPROVED",
        is_dry_run=False,
        idempotency_key="recent_mod_key",
        timestamp=recent_time,
    )
    test_db_session.add(recent_mod)

    # 3. Add expired cohost record
    old_cohost = CoHostAuditRecordModel(
        stream_id="stream_alpha",
        message_id="old_cohost_msg",
        author_id="u_old",
        author_name="OldChatter",
        intent="GREETING",
        intent_confidence=0.9,
        response_text="Hello from the past!",
        status="SENT",
        is_dry_run=False,
        idempotency_key="old_cohost_key",
        timestamp=old_time,
    )
    test_db_session.add(old_cohost)
    await test_db_session.commit()

    # 4. Prune records older than 30 days
    retention_mgr = AuditRetentionManager(test_db_session)
    result = await retention_mgr.prune_expired_records(retention_days=30)

    assert result["moderation_audits_deleted"] == 1
    assert result["cohost_audits_deleted"] == 1

    # Verify only recent_mod remains
    from app.db.repositories.moderation_repository import ModerationRepository
    mod_repo = ModerationRepository(test_db_session)
    remaining = await mod_repo.list_audits_for_stream("stream_alpha")
    assert len(remaining) == 1
    assert remaining[0].message_id == "recent_msg"
