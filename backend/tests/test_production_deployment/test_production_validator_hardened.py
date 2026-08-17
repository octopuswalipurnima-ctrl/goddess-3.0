"""
Tests for Hardened Production Configuration Validation in GODDESS AI 2.0.
"""

import pytest
from app.core.config import Settings
from app.core.validator import ConfigurationValidationError, validate_production_configuration


def test_production_validator_fails_on_weak_jwt_secret():
    """Verify production fails if SECRET_KEY is under 32 chars or contains insecure placeholders."""
    settings = Settings(
        environment="production",
        secret_key="short",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        auth_enabled=True,
        auth_dev_bypass=False,
        debug=False,
        rate_limit_enabled=True,
        cors_origins=["https://dashboard.example.com"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )
    with pytest.raises(ConfigurationValidationError) as exc:
        validate_production_configuration(settings)
    assert "SECRET_KEY must be at least 32 characters" in str(exc.value)


def test_production_validator_fails_on_debug_or_dev_bypass():
    """Verify production fails if DEBUG=true or AUTH_DEV_BYPASS=true."""
    settings = Settings(
        environment="production",
        secret_key="a" * 32,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        auth_enabled=True,
        auth_dev_bypass=True,  # Prohibited in production
        debug=True,            # Prohibited in production
        rate_limit_enabled=True,
        cors_origins=["https://dashboard.example.com"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )
    with pytest.raises(ConfigurationValidationError) as exc:
        validate_production_configuration(settings)
    assert "AUTH_DEV_BYPASS is strictly prohibited" in str(exc.value)
    assert "DEBUG mode must be disabled" in str(exc.value)


def test_production_validator_fails_on_wildcard_cors():
    """Verify production fails if CORS_ORIGINS contains wildcard '*'."""
    settings = Settings(
        environment="production",
        secret_key="a" * 32,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        auth_enabled=True,
        auth_dev_bypass=False,
        debug=False,
        rate_limit_enabled=True,
        cors_origins=["*"],  # Prohibited with credentials
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )
    with pytest.raises(ConfigurationValidationError) as exc:
        validate_production_configuration(settings)
    assert "Wildcard CORS ('*') is prohibited" in str(exc.value)


def test_production_validator_passes_on_valid_production_config():
    """Verify production validation succeeds when all parameters are properly configured."""
    settings = Settings(
        environment="production",
        secret_key="cryptographically_random_secure_key_12345678",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        auth_enabled=True,
        auth_dev_bypass=False,
        debug=False,
        rate_limit_enabled=True,
        cors_origins=["https://dashboard.goddessai.com"],
        youtube_api_key_1="AIzaSyValidLengthKey12345678901234",
        gemini_api_key_1="AIzaSyValidLengthGeminiKey123456789",
    )
    is_valid, issues, diagnostics = validate_production_configuration(settings)
    assert is_valid is True
    assert len(issues) == 0
