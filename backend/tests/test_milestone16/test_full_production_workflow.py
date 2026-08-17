"""
Tests for Complete Full Production Creator Workflow in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
import pytest
from app.core.safety_controller import safety_controller
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_full_production_creator_workflow():
    """Verify complete end-to-end operational workflow: overview -> safe mode -> audit."""
    overview = operations_manager.get_system_overview()
    assert overview.environment.upper() in ["DEVELOPMENT", "PRODUCTION", "TESTING"]

    # Toggle Safe Mode
    await operations_manager.enable_safe_mode("STREAM_A", reason="Maintenance Window")
    stream_ops = operations_manager.get_stream_operations("STREAM_A")
    assert stream_ops.safe_mode is True

    # Audit records exist
    records = operations_manager.audit.get_recent_records("STREAM_A", limit=10)
    assert len(records) > 0

    # Disable Safe Mode
    await operations_manager.disable_safe_mode("STREAM_A")
    stream_ops_recovered = operations_manager.get_stream_operations("STREAM_A")
    assert stream_ops_recovered.safe_mode is False
