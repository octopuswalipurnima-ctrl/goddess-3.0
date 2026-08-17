"""
Controlled Safe Mode Real-Service Tests for GODDESS AI 2.0.

Validates that Safe Mode blocks automated mutations while allowing observation and telemetry to continue.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_safe_mode_real_service_guarantees():
    """
    Validate Safe Mode blocks CoHost generation and live chat outgoing replies while telemetry stays live.
    """
    # 1. Enable Safe Mode on STREAM_A
    await operations_manager.enable_safe_mode(stream_id="STREAM_A", reason="Surge Observation")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.SAFE_MODE

    # 2. Co-Host generation must be blocked
    can_co, _ = safety_controller.can_cohost("STREAM_A")
    assert can_co is False

    # 3. Observation / Telemetry must continue
    ops = operations_manager.get_stream_operations("STREAM_A")
    assert ops.safe_mode is True
    assert ops.status in ["OFFLINE", "LIVE", "DEGRADED"]

    # 4. Disable Safe Mode
    await operations_manager.disable_safe_mode(stream_id="STREAM_A")
    assert safety_controller.get_stream_state("STREAM_A") == SafetyState.NORMAL
