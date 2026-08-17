"""
Tests for ModerationRepository operations, audit recording, and queries.
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.db.repositories.moderation_repository import ModerationRepository


@pytest.mark.asyncio
async def test_moderation_repository_recording_and_query(test_db_session):
    """Test recording moderation audit logs and querying by stream."""
    repo = ModerationRepository(test_db_session)

    # Record two decisions
    await repo.record_audit(
        stream_id="stream_alpha",
        message_id="m1",
        author_id="u1",
        author_name="User1",
        category="SPAM",
        confidence=0.95,
        severity="MEDIUM",
        recommended_action="DELETE",
        action_taken="DELETE",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="stream_alpha:m1:DELETE",
    )

    await repo.record_audit(
        stream_id="stream_alpha",
        message_id="m2",
        author_id="u2",
        author_name="User2",
        category="SAFE",
        confidence=0.99,
        severity="LOW",
        recommended_action="NONE",
        action_taken="NONE",
        action_status="APPROVED",
        is_dry_run=False,
        idempotency_key="stream_alpha:m2:NONE",
    )

    # Query for stream_alpha
    audits = await repo.list_audits_for_stream("stream_alpha", limit=10)
    assert len(audits) == 2

    # Filter by category
    spam_audits = await repo.list_audits_for_stream("stream_alpha", category="SPAM")
    assert len(spam_audits) == 1
    assert spam_audits[0].message_id == "m1"

    # Count
    count = await repo.count_audits_for_stream("stream_alpha")
    assert count == 2
