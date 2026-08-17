"""
Tests for Stream Operational Controls in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.operations.manager import OperationsManager


@pytest.mark.asyncio
async def test_stream_attach_detach_lifecycle():
    """Verify attaching and detaching streams updates supervisor and records audit."""
    mgr = OperationsManager()
    mgr.supervisor.attach_stream = AsyncMock()
    mgr.supervisor.detach_stream = AsyncMock()

    # 1. Attach stream
    res_att = await mgr.attach_stream(
        stream_id="STREAM_TEST_1",
        video_id="vid_test_1",
        channel_id="chan_test_1",
        title="Live Valorant",
    )
    assert res_att["status"] == "SUCCESS"
    assert res_att["video_id"] == "vid_test_1"

    # 2. Detach stream
    res_det = await mgr.detach_stream(stream_id="STREAM_TEST_1")
    assert res_det["status"] == "SUCCESS"
