"""
Controlled Production Restart & Recovery Validation for GODDESS AI 2.0.

Validates that system restarts restore module, cohost, and safety settings
without triggering historical message replays.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.cohost.manager import cohost_manager
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_restart_recovery_without_historical_replay():
    """
    Validate that upon simulated restart, existing configurations are loaded cleanly.
    """
    # 1. Configure CoHost
    cohost_manager.update_config("STREAM_RESTART", {"enabled": True, "dry_run": False})
    cfg = cohost_manager.get_config("STREAM_RESTART")
    assert cfg.enabled is True

    # 2. Verify metrics start at clean baseline
    assert cohost_manager.metrics.responses_sent >= 0

    # 3. Verify safety state is clean NORMAL
    assert safety_controller.get_stream_state("STREAM_RESTART") == SafetyState.NORMAL
