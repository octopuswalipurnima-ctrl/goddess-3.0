"""
Tests for Centralized Settings & Configuration Manager.
"""

from app.core.config import Settings


def test_default_settings():
    """Verify default settings initialization."""
    settings = Settings()
    assert settings.app_name == "Goddess AI 2.0"
    assert settings.app_version == "2.0.0"
    assert settings.environment in ["development", "test", "production"]
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0


def test_youtube_api_keys_property():
    """Verify that only non-empty YouTube API keys are returned."""
    # When no keys configured
    settings = Settings(
        youtube_api_key_1=None,
        youtube_api_key_2="",
        youtube_api_key_3="   ",
        youtube_api_key_4=None,
    )
    assert settings.youtube_api_keys == []
    assert settings.is_youtube_configured is False

    # When 2 keys configured
    settings_with_keys = Settings(
        youtube_api_key_1="AIzaSyDummyKeyOne12345",
        youtube_api_key_2=None,
        youtube_api_key_3="AIzaSyDummyKeyThree67890",
    )
    assert len(settings_with_keys.youtube_api_keys) == 2
    assert settings_with_keys.is_youtube_configured is True
    assert "AIzaSyDummyKeyOne12345" in settings_with_keys.youtube_api_keys
    assert "AIzaSyDummyKeyThree67890" in settings_with_keys.youtube_api_keys


def test_gemini_api_keys_property():
    """Verify that only non-empty Gemini API keys are returned."""
    settings = Settings(
        gemini_api_key_1=None,
        gemini_api_key_2=None,
    )
    assert settings.gemini_api_keys == []
    assert settings.is_gemini_configured is False

    settings_with_key = Settings(
        gemini_api_key_1="AIzaSyGeminiKey12345",
    )
    assert len(settings_with_key.gemini_api_keys) == 1
    assert settings_with_key.is_gemini_configured is True


def test_cors_origins_parsing():
    """Verify CORS origins string and list parsing."""
    # From comma-separated string
    settings = Settings(cors_origins="http://localhost:3000, https://myapp.com")
    assert "http://localhost:3000" in settings.cors_origins
    assert "https://myapp.com" in settings.cors_origins

    # From JSON array string
    settings_json = Settings(cors_origins='["http://localhost:3000", "http://localhost:8000"]')
    assert len(settings_json.cors_origins) == 2
