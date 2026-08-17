"""
Tests for Zero Historical Replay on State Recovery in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.operations.manager import OperationsManager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_clearing_emergency_stop_does_not_replay_suppressed_messages():
    """Verify clearing emergency stop does not trigger queued / suppressed messages."""
    mgr = OperationsManager()

    # Trigger emergency stop
    await mgr.trigger_emergency_stop(stream_id="STREAM_NOREPLAY", reason="Simulated outage")
    initial_sent = mgr.cohost.metrics.responses_sent

    # Clear emergency stop
    await mgr.clear_emergency_stop(stream_id="STREAM_NOREPLAY")

    # Metrics sent count must remain unchanged (no back-replay)
    assert mgr.cohost.metrics.responses_sent == initial_sent
