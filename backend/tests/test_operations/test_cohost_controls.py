"""
Tests for CoHost Operational Controls in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.manager import OperationsManager


@pytest.mark.asyncio
async def test_cohost_enable_and_dry_run_toggles():
    """Verify operational toggles for CoHost enable/disable and dry-run."""
    mgr = OperationsManager()

    # 1. Enable CoHost
    res1 = await mgr.set_cohost_enabled("STREAM_CO_OPS", True)
    assert res1["status"] == "SUCCESS"
    assert mgr.cohost.get_config("STREAM_CO_OPS").enabled is True

    # 2. Toggle Dry-Run
    res2 = await mgr.set_cohost_dry_run("STREAM_CO_OPS", False)
    assert res2["status"] == "SUCCESS"
    assert mgr.cohost.get_config("STREAM_CO_OPS").dry_run is False
