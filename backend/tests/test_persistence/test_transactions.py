"""
Tests for transaction safety, session rollback, and broken connection handling.
"""

import pytest
from sqlalchemy import select
from app.db.models.stream import StreamModel
from app.db.repositories.stream_repository import StreamRepository


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(test_db_session):
    """Verify that an exception within a transaction cleanly rolls back changes."""
    repo = StreamRepository(test_db_session)

    # 1. Create a stream
    await repo.create_or_update_stream(stream_id="stream_stable", status="ACTIVE")
    await test_db_session.commit()

    # 2. Try an operation that fails within a nested savepoint or transaction
    try:
        # Create uncommitted stream and raise error
        stream_temp = StreamModel(stream_id="stream_temp", status="RUNNING")
        test_db_session.add(stream_temp)
        raise ValueError("Simulated unexpected failure during processing")
    except ValueError:
        await test_db_session.rollback()

    # 3. Verify stream_temp was NOT committed, but stream_stable still exists
    res = await test_db_session.execute(select(StreamModel).where(StreamModel.stream_id == "stream_temp"))
    assert res.scalar_one_or_none() is None

    res_stable = await test_db_session.execute(select(StreamModel).where(StreamModel.stream_id == "stream_stable"))
    assert res_stable.scalar_one_or_none() is not None
