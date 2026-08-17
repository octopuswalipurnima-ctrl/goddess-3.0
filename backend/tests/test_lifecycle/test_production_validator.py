"""
Production Configuration Validator Tests for GODDESS AI 2.0.

Verifies strict FAIL-CLOSED policy in production when insecure or missing parameters are detected.
"""

import pytest
from app.core.config import Settings
from app.core.validator import ConfigurationValidationError, validate_production_configuration


def test_production_validator_rejects_weak_secret_key():
    """Verify production mode rejects weak/insecure SECRET_KEY."""
    prod_settings = Settings(
        environment="production",
        secret_key="insecure-default-key",
        debug=False,
        auth_enabled=True,
        auth_dev_bypass=False,
        rate_limit_enabled=True,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        cors_origins=["https://dashboard.example.com"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )

    with pytest.raises(ConfigurationValidationError) as exc:
        validate_production_configuration(prod_settings)
    assert "SECRET_KEY" in str(exc.value)


def test_production_validator_rejects_wildcard_cors():
    """Verify production mode rejects wildcard '*' CORS origins."""
    prod_settings = Settings(
        environment="production",
        secret_key="a" * 40,
        debug=False,
        auth_enabled=True,
        auth_dev_bypass=False,
        rate_limit_enabled=True,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        cors_origins=["*"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )

    with pytest.raises(ConfigurationValidationError) as exc:
        validate_production_configuration(prod_settings)
    assert "Wildcard CORS" in str(exc.value)


def test_production_validator_accepts_valid_prod_config():
    """Verify production mode accepts strong, secure configuration."""
    prod_settings = Settings(
        environment="production",
        secret_key="a" * 40,
        debug=False,
        auth_enabled=True,
        auth_dev_bypass=False,
        rate_limit_enabled=True,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        cors_origins=["https://dashboard.example.com"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )

    is_valid, issues, diag = validate_production_configuration(prod_settings)
    assert is_valid is True
    assert len(issues) == 0
    assert diag["is_valid"] is True


def test_development_mode_permits_safe_defaults():
    """Verify development mode produces diagnostic warnings without raising fatal exceptions."""
    dev_settings = Settings(
        environment="development",
        secret_key="development-insecure-secret-key-change-in-production-min-32-chars",
        debug=True,
        auth_enabled=True,
        auth_dev_bypass=False,
    )

    is_valid, issues, diag = validate_production_configuration(dev_settings)
    assert is_valid is False
    assert len(issues) > 0  # Contains warnings
