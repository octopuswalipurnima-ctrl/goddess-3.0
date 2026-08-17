"""
Tests for Application Startup Validation and Lifespan Initialization.
"""

import pytest
from app.core.config import settings
from app.main import lifespan, app


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown():
    """Verify application starts and shuts down cleanly without exceptions."""
    async with lifespan(app):
        assert settings.app_name == "Goddess AI 2.0"
