"""
Pytest configuration and fixtures for GODDESS AI 2.0.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def default_test_settings(monkeypatch):
    """
    Default fixture ensuring test isolation and development auth bypass for legacy test suites.
    Security suites explicitly override this to test 401/403 rejections.
    """
    monkeypatch.setattr("app.core.config.settings.auth_dev_bypass", True)


@pytest.fixture(autouse=True)
async def clean_safety_state():
    """
    Ensure safety_controller starts and ends in a clean NORMAL state for every test.
    """
    from app.core.safety_controller import safety_controller
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.fixture
async def async_client():
    """Async HTTP test client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
