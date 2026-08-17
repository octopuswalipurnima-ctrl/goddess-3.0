"""
Tests for ProductionSafetyController in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import ProductionSafetyController, SafetyState


@pytest.mark.asyncio
async def test_safety_controller_default_normal_state():
    """Verify safety controller initializes in NORMAL state and allows standard operations."""
    ctrl = ProductionSafetyController()
    assert ctrl.global_state == SafetyState.NORMAL
    assert ctrl.is_global_emergency is False
    assert ctrl.is_global_safe_mode is False

    allowed, reason = ctrl.can_moderate("STREAM_1")
    assert allowed is True
    assert reason == "Allowed"

    allowed, _ = ctrl.can_cohost("STREAM_1")
    assert allowed is True

    allowed, _ = ctrl.can_send_chat("STREAM_1")
    assert allowed is True

    allowed, _ = ctrl.can_execute_command("STREAM_1")
    assert allowed is True


@pytest.mark.asyncio
async def test_global_emergency_stop_blocks_all_actions():
    """Verify triggering global emergency stop halts all moderation, cohost, and chat actions."""
    ctrl = ProductionSafetyController()
    await ctrl.trigger_emergency_stop(reason="Security incident", triggered_by="admin")

    assert ctrl.global_state == SafetyState.EMERGENCY_STOP
    assert ctrl.is_global_emergency is True

    # Check all actions are blocked
    allowed, reason = ctrl.can_moderate("STREAM_1")
    assert allowed is False
    assert "Emergency Stop" in reason

    allowed, reason = ctrl.can_cohost("STREAM_1")
    assert allowed is False
    assert "Emergency Stop" in reason

    allowed, reason = ctrl.can_send_chat("STREAM_1")
    assert allowed is False

    allowed, reason = ctrl.can_execute_command("STREAM_1")
    assert allowed is False

    # Clear emergency stop
    await ctrl.clear_emergency_stop(cleared_by="admin")
    assert ctrl.global_state == SafetyState.NORMAL
    assert ctrl.is_global_emergency is False

    allowed, _ = ctrl.can_moderate("STREAM_1")
    assert allowed is True


@pytest.mark.asyncio
async def test_per_stream_emergency_stop_isolation():
    """Verify emergency stop on STREAM_A does NOT affect STREAM_B."""
    ctrl = ProductionSafetyController()
    await ctrl.trigger_emergency_stop(stream_id="STREAM_A", reason="Raid attack", triggered_by="mod")

    assert ctrl.is_stream_emergency("STREAM_A") is True
    assert ctrl.is_stream_emergency("STREAM_B") is False

    # STREAM_A actions blocked
    allowed, reason = ctrl.can_send_chat("STREAM_A")
    assert allowed is False
    assert "Emergency Stop" in reason

    # STREAM_B actions allowed
    allowed, reason = ctrl.can_send_chat("STREAM_B")
    assert allowed is True
    assert reason == "Allowed"


@pytest.mark.asyncio
async def test_safe_mode_gates():
    """Verify Safe Mode allows read/logging evaluation but blocks automated outgoing chat and AI replies."""
    ctrl = ProductionSafetyController()
    await ctrl.enable_safe_mode(stream_id="STREAM_SAFE", reason="High volatility")

    assert ctrl.is_stream_safe_mode("STREAM_SAFE") is True

    # Co-Host reply generation is paused
    allowed, reason = ctrl.can_cohost("STREAM_SAFE")
    assert allowed is False
    assert "Safe mode" in reason

    # Outgoing chat is blocked
    allowed, reason = ctrl.can_send_chat("STREAM_SAFE")
    assert allowed is False
    assert "Safe mode" in reason

    await ctrl.disable_safe_mode(stream_id="STREAM_SAFE")
    assert ctrl.is_stream_safe_mode("STREAM_SAFE") is False
