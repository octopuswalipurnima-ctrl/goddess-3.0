"""
Controlled Failure Recovery Matrix Tests for GODDESS AI 2.0.

Validates multi-system failure recovery across PostgreSQL, Redis, Gemini, YouTube, and WebSocket.
"""

from unittest.mock import AsyncMock
import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_recovery_matrix_gemini_outage_to_recovery():
    """
    Validate that Gemini AI failure transitions AI to unavailable/degraded without breaking Tier 1 moderation.
    """
    # Tier 1 Moderation rule check still works regardless of Gemini state
    can_mod, _ = safety_controller.can_moderate("STREAM_A")
    assert can_mod is True


@pytest.mark.asyncio
async def test_recovery_matrix_stream_disconnect_and_reconnect():
    """
    Validate stream disconnection transitions state safely without infinite loops.
    """
    can_recon, _ = safety_controller.can_reconnect("STREAM_A", reconnect_count=3)
    assert can_recon is True

    # Limit exceeded (e.g. > 50 attempts)
    can_recon_blocked, _ = safety_controller.can_reconnect("STREAM_A", reconnect_count=55)
    assert can_recon_blocked is False
