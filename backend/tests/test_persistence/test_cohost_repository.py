"""
Tests for CoHostRepository operations, configuration, and audits.
"""

import pytest
from app.db.repositories.cohost_repository import CoHostRepository


@pytest.mark.asyncio
async def test_cohost_repository_config_and_audit(test_db_session):
    """Test saving Co-Host configurations and recording response audit events."""
    repo = CoHostRepository(test_db_session)

    # 1. Set Config
    cfg = await repo.set_config(
        stream_id="stream_alpha",
        enabled=True,
        dry_run=False,
        personality_name="playful",
        cooldown_seconds=10.0,
    )
    assert cfg.stream_id == "stream_alpha"
    assert cfg.personality_name == "playful"

    # 2. Record Audit
    audit = await repo.record_audit(
        stream_id="stream_alpha",
        message_id="msg_q1",
        author_id="user_v1",
        author_name="StreamFan",
        intent="QUESTION",
        intent_confidence=0.88,
        response_text="We are playing Elden Ring today!",
        status="SENT",
        is_dry_run=False,
        idempotency_key="cohost:stream_alpha:msg_q1",
    )
    assert audit.intent == "QUESTION"
    assert audit.response_text == "We are playing Elden Ring today!"

    # 3. Query Audits
    logs = await repo.list_audits_for_stream("stream_alpha")
    assert len(logs) == 1
    assert logs[0].author_name == "StreamFan"
