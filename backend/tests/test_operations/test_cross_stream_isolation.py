"""
Tests for Zero Cross-Stream Operational Contamination in GODDESS AI 2.0.
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
async def test_cross_stream_operational_isolation():
    """Verify modifying safe mode on STREAM_A never alters STREAM_B, STREAM_C, or STREAM_D."""
    mgr = OperationsManager()

    await mgr.enable_safe_mode(stream_id="STREAM_A", reason="Test safe mode on A")

    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.SAFE_MODE
    assert safety_controller.get_stream_state("STREAM_B") == SafetyState.NORMAL
    assert safety_controller.get_stream_state("STREAM_C") == SafetyState.NORMAL
    assert safety_controller.get_stream_state("STREAM_D") == SafetyState.NORMAL
