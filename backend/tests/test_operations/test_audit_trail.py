"""
Tests for Operational Audit Trail in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.audit import OperationalAuditService


@pytest.mark.asyncio
async def test_audit_trail_records_and_retrieves_records():
    """Verify audit service records structured entries and honors bounds."""
    audit = OperationalAuditService(max_buffer_size=10)

    for i in range(15):
        await audit.record_audit(
            action=f"ACTION_{i}",
            actor_id="creator_1",
            actor_role="OWNER",
            stream_id="STREAM_A",
            target=f"target_{i}",
        )

    records = audit.get_recent_records(stream_id="STREAM_A", limit=50)
    assert len(records) == 10  # Bounded to 10
    assert records[0].action == "ACTION_14"  # Newest first
