"""
Tests for CoHost Decision Telemetry and Metrics Tracking in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.cohost.manager import CoHostManager
from app.services.cohost.models import ResponseStatus
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_cohost_metrics_and_telemetry_tracking():
    """Verify metrics increment accurately during message analysis and engagement decisions."""
    mgr = CoHostManager()
    mgr.update_config("STREAM_TELEM", {"enabled": True, "dry_run": True})

    # Message 1: Noise (ignored)
    msg1 = ChatMessage(
        message_id="m_t1",
        stream_id="STREAM_TELEM",
        author_id="u1",
        author_name="Alice",
        message_text="!",
    )
    await mgr.process_message(msg1)

    assert mgr.metrics.messages_analyzed >= 1
    assert mgr.metrics.messages_ignored >= 1
    assert mgr.metrics.engagement_decisions >= 1
