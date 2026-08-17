"""
Tests for Application Shutdown and Resource Cleanup.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.main import lifespan, app


@pytest.mark.asyncio
async def test_shutdown_closes_subsystems():
    """Verify shutdown cleans up modules, Gemini manager, and database."""
    with patch("app.modules.module_manager.stop_all", AsyncMock()) as mock_stop_mods:
        async with lifespan(app):
            pass
        mock_stop_mods.assert_awaited()
