"""
Tests for persistent SQLAlchemy model metadata, schemas, and constraints.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.db.models import (
    CoHostAuditRecordModel,
    CoHostConfigModel,
    CreatorSettingsModel,
    ModerationAuditRecordModel,
    ModuleConfigModel,
    StreamConfigModel,
    StreamModel,
)


@pytest.mark.asyncio
async def test_stream_model_creation(test_db_session):
    """Test creating and persisting StreamModel and StreamConfigModel."""
    stream = StreamModel(
        stream_id="stream_alpha",
        channel_id="UC123456789",
        title="Goddess Live Stream",
        status="ACTIVE",
        started_at=datetime.now(timezone.utc),
    )
    test_db_session.add(stream)

    cfg = StreamConfigModel(
        stream_id="stream_alpha",
        enabled=True,
        config_data={"max_chat_rate": 60},
    )
    test_db_session.add(cfg)
    await test_db_session.commit()

    # Query back
    result = await test_db_session.execute(select(StreamModel).where(StreamModel.stream_id == "stream_alpha"))
    fetched = result.scalar_one()
    assert fetched.stream_id == "stream_alpha"
    assert fetched.title == "Goddess Live Stream"
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_moderation_audit_model_creation(test_db_session):
    """Test creating and persisting ModerationAuditRecordModel."""
    record = ModerationAuditRecordModel(
        stream_id="stream_beta",
        message_id="msg_001",
        author_id="user_123",
        author_name="BadUser",
        category="SPAM",
        confidence=0.92,
        severity="MEDIUM",
        recommended_action="DELETE",
        action_taken="DELETE",
        action_status="EXECUTED",
        is_dry_run=False,
        reason="Repeated spam detected",
        idempotency_key="stream_beta:msg_001:DELETE",
    )
    test_db_session.add(record)
    await test_db_session.commit()

    result = await test_db_session.execute(
        select(ModerationAuditRecordModel).where(ModerationAuditRecordModel.idempotency_key == "stream_beta:msg_001:DELETE")
    )
    fetched = result.scalar_one()
    assert fetched.author_name == "BadUser"
    assert fetched.confidence == 0.92
