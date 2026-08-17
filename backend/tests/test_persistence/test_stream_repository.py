"""
Tests for StreamRepository operations and multi-stream persistence isolation.
"""

import pytest
from app.db.repositories.stream_repository import StreamRepository


@pytest.mark.asyncio
async def test_stream_repository_crud(test_db_session):
    """Test creating, updating, and querying streams via StreamRepository."""
    repo = StreamRepository(test_db_session)

    # 1. Create Stream
    stream = await repo.create_or_update_stream(
        stream_id="stream_alpha",
        channel_id="UC_ALPHA",
        title="Stream Alpha Gaming",
        status="ACTIVE",
    )
    assert stream.stream_id == "stream_alpha"
    assert stream.status == "ACTIVE"

    # 2. Update Stream Status
    updated = await repo.update_status("stream_alpha", "STOPPED")
    assert updated is not None
    assert updated.status == "STOPPED"

    # 3. Stream Config
    cfg = await repo.set_config("stream_alpha", {"moderation_enabled": True}, enabled=True)
    assert cfg.enabled is True
    assert cfg.config_data["moderation_enabled"] is True

    # 4. Fetch Config
    fetched_cfg = await repo.get_config("stream_alpha")
    assert fetched_cfg is not None
    assert fetched_cfg.config_data["moderation_enabled"] is True
