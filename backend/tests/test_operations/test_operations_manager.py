"""
Tests for Operations Manager Orchestration in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.services.operations.manager import OperationsManager


@pytest.mark.asyncio
async def test_operations_manager_aggregates_overview_and_health():
    """Verify operations manager collects valid system overview and detailed health."""
    mgr = OperationsManager()

    overview = mgr.get_system_overview()
    assert overview.version == "2.0.0"
    assert overview.production_mode == "PRODUCTION_SAFE"

    detailed = mgr.get_detailed_health()
    assert detailed.version == "2.0.0"
    assert "STREAM_A" in detailed.streams
    assert "STREAM_B" in detailed.streams
    assert "STREAM_C" in detailed.streams
    assert "STREAM_D" in detailed.streams
