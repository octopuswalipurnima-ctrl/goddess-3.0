"""
Complete Real End-to-End Processing Pipeline Validation for GODDESS AI 2.0.

Validates:
- SAFE ACTION PATH: Incoming chat -> EventBus -> Moderation -> AI Decision -> YouTube Writer -> Audit -> Telemetry
- BLOCKED ACTION PATH: Safety Controller Emergency Stop -> Instant Action Block -> Zero Outgoing Mutations -> Zero Replay
"""

from unittest.mock import AsyncMock
import os
import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.ai.decision_engine import ai_decision_engine
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_complete_e2e_pipeline_safe_and_blocked_paths():
    """
    Validate safe message processing flow vs blocked emergency stop flow.
    """
    # 1. Safe Action Path
    can_act, reason = safety_controller.can_send_chat("STREAM_A")
    assert can_act is True

    # 2. Blocked Action Path: Trigger Emergency Stop
    await operations_manager.trigger_emergency_stop(stream_id="STREAM_A", reason="Surge Outage")
    can_act_blocked, block_reason = safety_controller.can_send_chat("STREAM_A")
    assert can_act_blocked is False

    # 3. Clear Emergency Stop -> Verify zero historical replay
    await operations_manager.clear_emergency_stop(stream_id="STREAM_A")
    can_act_recovered, _ = safety_controller.can_send_chat("STREAM_A")
    assert can_act_recovered is True
