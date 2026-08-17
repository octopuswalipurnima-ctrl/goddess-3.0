"""
Tests for Production Health Supervisor in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.health_supervisor import ProductionHealthSupervisor


@pytest.mark.asyncio
async def test_health_supervisor_lifecycle_and_check():
    """Verify health supervisor starts, executes check, and stops cleanly."""
    supervisor = ProductionHealthSupervisor(check_interval_seconds=1.0)
    await supervisor.start()
    assert supervisor.is_running is True

    report = await supervisor.check_all_now()
    assert "overall_status" in report
    assert "components" in report
    assert "circuit_breakers" in report

    await supervisor.stop()
    assert supervisor.is_running is False
