"""
Tests for Global Emergency Stop Halting All Mutations in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.manager import OperationsManager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_global_emergency_stop_blocks_all_streams():
    """Verify global emergency stop sets state to EMERGENCY_STOP across all streams."""
    mgr = OperationsManager()

    # Trigger global emergency stop
    res = await mgr.trigger_emergency_stop(stream_id=None, reason="Critical Drill")
    assert res["status"] == "SUCCESS"
    assert res["scope"] == "GLOBAL"
    assert safety_controller.is_global_emergency is True

    # Verify gates on all streams
    for sid in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        can_chat, _ = safety_controller.can_send_chat(sid)
        can_co, _ = safety_controller.can_cohost(sid)
        assert can_chat is False
        assert can_co is False
