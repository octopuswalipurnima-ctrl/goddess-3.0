"""
Tests for Graceful Shutdown Transitions in GODDESS AI 2.0.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_graceful_shutdown_transitions_safety_state():
    """Verify entering shutting down state blocks all subsequent mutations."""
    await safety_controller.enter_shutting_down()
    assert safety_controller.is_shutting_down is True

    can_mutate, _ = safety_controller.can_mutate_stream("STREAM_A")
    assert can_mutate is False
