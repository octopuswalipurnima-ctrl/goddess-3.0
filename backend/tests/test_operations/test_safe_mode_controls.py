"""
Tests for Safe Mode Controls in GODDESS AI 2.0.
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
async def test_safe_mode_enable_and_disable():
    """Verify safe mode blocks CoHost generation without stopping stream session."""
    mgr = OperationsManager()

    await mgr.enable_safe_mode(stream_id="STREAM_SM", reason="Chat surge")
    assert safety_controller.get_stream_state("STREAM_SM") == SafetyState.SAFE_MODE

    can_co, _ = safety_controller.can_cohost("STREAM_SM")
    assert can_co is False

    await mgr.disable_safe_mode(stream_id="STREAM_SM")
    assert safety_controller.get_stream_state("STREAM_SM") == SafetyState.NORMAL
