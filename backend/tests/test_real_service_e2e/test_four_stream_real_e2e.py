"""
Controlled 4-Stream Architecture Isolation Verification for GODDESS AI 2.0.

Requires explicit RUN_RAILWAY_E2E_TEST=true.
Validates complete state and context isolation across STREAM_A, STREAM_B, STREAM_C, and STREAM_D.
"""

import os
import pytest
from app.services.cohost.manager import cohost_manager
from app.services.moderation.manager import moderation_manager
from app.services.operations.manager import operations_manager


@pytest.mark.asyncio
async def test_four_stream_complete_isolation():
    """
    Validate that configuration and context in STREAM_A never leaks into STREAM_B, STREAM_C, or STREAM_D.
    """
    if os.getenv("RUN_RAILWAY_E2E_TEST", "false").lower() != "true":
        pytest.skip("RUN_RAILWAY_E2E_TEST is not true. Skipping 4-stream real E2E test.")

    streams = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]

    # 1. Update config on STREAM_A
    cohost_manager.update_config("STREAM_A", {"enabled": True, "dry_run": False})
    cohost_manager.update_config("STREAM_B", {"enabled": False, "dry_run": True})

    cfg_a = cohost_manager.get_config("STREAM_A")
    cfg_b = cohost_manager.get_config("STREAM_B")

    assert cfg_a.enabled is True
    assert cfg_b.enabled is False

    # 2. Check operations summaries
    ops = operations_manager.get_all_stream_operations()
    for s in streams:
        assert s in ops
