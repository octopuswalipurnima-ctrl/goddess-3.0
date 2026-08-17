"""
Tests for Failure Recovery Matrices in GODDESS AI 2.0.
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
async def test_failure_recovery_safe_clearing():
    """Verify system transitions gracefully during failure and recovery cycles."""
    mgr = OperationsManager()

    # 1. Failure occurrence -> Emergency stop triggered
    await mgr.trigger_emergency_stop(reason="Dependency failure")
    assert safety_controller.is_global_emergency is True

    # 2. Recovery -> Clear emergency stop
    await mgr.clear_emergency_stop()
    assert safety_controller.is_global_emergency is False
    assert safety_controller.global_state == SafetyState.NORMAL
