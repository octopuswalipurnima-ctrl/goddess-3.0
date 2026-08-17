"""
Tests for Emergency Stop Authority Hardening in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_emergency_stop_authoritative_block():
    """Verify emergency stop blocks all outgoing operations."""
    await safety_controller.trigger_emergency_stop(reason="Security Incident")
    assert safety_controller.is_global_emergency is True

    can_chat, _ = safety_controller.can_send_chat("STREAM_A")
    can_mod, _ = safety_controller.can_moderate("STREAM_A")
    can_cmd, _ = safety_controller.can_execute_command("STREAM_A")

    assert can_chat is False
    assert can_mod is False
    assert can_cmd is False
