"""
Tests for ModerationAuditLogger and In-Memory Bounded History.
"""

import pytest
from app.services.moderation.audit import ModerationAuditLogger
from app.services.moderation.models import (
    ActionStatus,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
)


@pytest.mark.asyncio
async def test_audit_logger_records_and_bounds():
    """Verify recording of audit entries and bounded buffer enforcement."""
    logger = ModerationAuditLogger(max_records_per_stream=3)

    for i in range(5):
        dec = ModerationDecision(
            message_id=f"m_audit_{i}",
            stream_id="stream_1",
            author_id=f"user_{i}",
            author_name=f"User{i}",
            category=ModerationCategory.SPAM,
            recommended_action=ModerationAction.DELETE,
        )
        await logger.record_audit(
            decision=dec,
            action_taken=ModerationAction.DELETE,
            action_status=ActionStatus.EXECUTED,
        )

    records = logger.get_recent_records("stream_1", limit=10)
    assert len(records) == 3
    # Latest 3 records: m_audit_2, m_audit_3, m_audit_4
    assert records[-1].message_id == "m_audit_4"
