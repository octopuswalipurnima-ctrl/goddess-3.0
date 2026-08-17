"""
Tests for Emergency Stop Halting Co-Host in GODDESS AI 2.0.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import safety_controller
from app.services.cohost.manager import CoHostManager
from app.services.youtube.models import ChatMessage


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_global_emergency_stop_halts_cohost_immediately():
    """Verify global emergency stop completely silences Co-Host across all streams."""
    mgr = CoHostManager()
    for s in ["STREAM_A", "STREAM_B"]:
        mgr.update_config(s, {"enabled": True, "dry_run": False})

    await safety_controller.trigger_emergency_stop(stream_id=None, reason="Critical drill")

    for s in ["STREAM_A", "STREAM_B"]:
        can_co, _ = safety_controller.can_cohost(s)
        can_chat, _ = safety_controller.can_send_chat(s)
        assert can_co is False
        assert can_chat is False
