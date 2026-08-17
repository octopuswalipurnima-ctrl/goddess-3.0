"""
Tests for Moderation Operational Controls in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.manager import OperationsManager


@pytest.mark.asyncio
async def test_moderation_enable_and_disable_toggles():
    """Verify moderation enabled state toggles correctly and logs audit event."""
    mgr = OperationsManager()

    res_dis = await mgr.set_moderation_enabled("STREAM_MOD_OPS", False)
    assert res_dis["status"] == "SUCCESS"
    assert mgr.moderation.get_config("STREAM_MOD_OPS").enabled is False

    res_en = await mgr.set_moderation_enabled("STREAM_MOD_OPS", True)
    assert res_en["status"] == "SUCCESS"
    assert mgr.moderation.get_config("STREAM_MOD_OPS").enabled is True
