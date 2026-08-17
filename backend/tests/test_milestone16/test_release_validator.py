"""
Tests for Production Release Gate Validator in GODDESS AI 2.0.
"""

import pytest
from app.core.config import Settings
from app.core.release_validator import ProductionReleaseValidator, release_validator


@pytest.mark.asyncio
async def test_release_validator_healthy_default():
    """Verify release validator executes cleanly in development/testing mode."""
    res = await release_validator.validate_release()
    assert res.version == "2.0.0"
    assert "configuration" in res.checks
    assert "safety_controller" in res.checks
    assert isinstance(res.passed, bool)


@pytest.mark.asyncio
async def test_release_validator_blocks_production_debug_mode():
    """Verify release validator blocks production startup when DEBUG is True."""
    cfg = Settings(
        environment="production",
        debug=True,
        secret_key="a-very-long-production-cryptographically-secure-key-32-chars",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        youtube_api_key_1="AIzaSyA12345678901234567890123456789012",
        gemini_api_key_1="AIzaSyB12345678901234567890123456789012",
        cors_origins=["https://dashboard.goddessai.app"],
    )
    validator = ProductionReleaseValidator(cfg)
    res = await validator.validate_release()

    assert res.passed is False
    assert any("DEBUG" in b for b in res.blockers)
