"""
Tests for persistence layer idempotency preventing duplicate actions.
"""

import pytest
from app.db.repositories.moderation_repository import ModerationRepository


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_audit_record(test_db_session):
    """Verify that submitting an audit record with the same idempotency key returns the existing record."""
    repo = ModerationRepository(test_db_session)

    # First record
    rec1 = await repo.record_audit(
        stream_id="stream_alpha",
        message_id="msg_duplicate",
        author_id="user_spammer",
        author_name="Spammer",
        category="SPAM",
        confidence=0.99,
        severity="HIGH",
        recommended_action="TIMEOUT",
        action_taken="TIMEOUT",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="stream_alpha:msg_duplicate:TIMEOUT",
    )

    # Second record with identical idempotency key
    rec2 = await repo.record_audit(
        stream_id="stream_alpha",
        message_id="msg_duplicate",
        author_id="user_spammer",
        author_name="Spammer",
        category="SPAM",
        confidence=0.99,
        severity="HIGH",
        recommended_action="TIMEOUT",
        action_taken="TIMEOUT",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="stream_alpha:msg_duplicate:TIMEOUT",
    )

    assert rec1.id == rec2.id

    # Total audits in DB should be exactly 1
    total = await repo.count_audits_for_stream("stream_alpha")
    assert total == 1
