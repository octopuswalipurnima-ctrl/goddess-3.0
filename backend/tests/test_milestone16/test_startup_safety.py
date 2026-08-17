"""
Tests for Application Startup Safety Gates in GODDESS AI 2.0.
"""

import pytest
from app.core.config import Settings
from app.core.validator import ConfigurationValidationError, validate_production_configuration


def test_startup_safety_gate_rejects_weak_production_secrets():
    """Verify startup fails closed when insecure secret key is supplied in production."""
    cfg = Settings(
        environment="production",
        debug=False,
        secret_key="insecure-placeholder-key-test",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        youtube_api_key_1="AIzaSyA12345678901234567890123456789012",
        gemini_api_key_1="AIzaSyB12345678901234567890123456789012",
        cors_origins=["https://dashboard.goddessai.app"],
    )

    with pytest.raises(ConfigurationValidationError) as exc_info:
        validate_production_configuration(cfg)

    assert "safety violation" in str(exc_info.value)
