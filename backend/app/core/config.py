"""
Centralized Configuration Manager for GODDESS AI 2.0.

Loads settings from environment variables and local .env files using modern Pydantic v2 Settings.
Enforces validation, defaults, secret masking, and multi-key rotation structures.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Information
    app_name: str = Field(default="Goddess AI 2.0", description="Application display name")
    app_version: str = Field(default="2.0.0", description="Application semantic version")
    environment: str = Field(default="development", description="Runtime environment (development, test, production)")
    debug: bool = Field(default=True, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Standard logging level")
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, description="Server bind port")

    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origin URLs",
    )

    # Database & Redis (Optional / Not Configured in Milestone 0)
    database_url: Optional[str] = Field(default=None, description="PostgreSQL async connection URL")
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")

    # YouTube Data API Credentials (Up to 4 Rotated Keys)
    youtube_api_key_1: Optional[str] = Field(default=None, description="Primary YouTube API Key")
    youtube_api_key_2: Optional[str] = Field(default=None, description="Secondary YouTube API Key")
    youtube_api_key_3: Optional[str] = Field(default=None, description="Tertiary YouTube API Key")
    youtube_api_key_4: Optional[str] = Field(default=None, description="Quaternary YouTube API Key")

    # Gemini AI API Credentials (Up to 4 Rotated Keys)
    gemini_api_key_1: Optional[str] = Field(default=None, description="Primary Gemini API Key")
    gemini_api_key_2: Optional[str] = Field(default=None, description="Secondary Gemini API Key")
    gemini_api_key_3: Optional[str] = Field(default=None, description="Tertiary Gemini API Key")
    gemini_api_key_4: Optional[str] = Field(default=None, description="Quaternary Gemini API Key")

    # Gemini Model Defaults
    gemini_primary_model: str = Field(default="gemini-2.5-flash", description="Primary Gemini Model Name")
    gemini_fallback_model: str = Field(default="gemini-2.5-flash-lite", description="Fallback Gemini Model Name")
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="AI Temperature")
    gemini_max_output_tokens: int = Field(default=512, gt=0, description="Max AI Output Tokens")
    gemini_request_timeout: float = Field(default=10.0, gt=0.0, description="Gemini API timeout in seconds")
    gemini_max_concurrency: int = Field(default=2, gt=0, description="Max concurrent Gemini API requests")
    gemini_queue_max_size: int = Field(default=100, gt=0, description="Max pending requests in AI queue")
    gemini_rate_limit_capacity: int = Field(default=5, gt=0, description="Rate limiter token bucket capacity")
    gemini_rate_limit_refill_rate: float = Field(default=0.5, gt=0.0, description="Rate limiter refill tokens per second")
    gemini_max_retries: int = Field(default=3, ge=0, description="Max retry attempts for retryable errors")

    # Security
    secret_key: str = Field(
        default="development-insecure-secret-key-change-in-production-min-32-chars",
        description="Cryptographic secret key for JWT/session management",
    )
    access_token_expire_minutes: int = Field(default=1440, description="Access token expiration in minutes")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def youtube_api_keys(self) -> List[str]:
        """Return list of active non-empty YouTube API keys."""
        keys = [
            self.youtube_api_key_1,
            self.youtube_api_key_2,
            self.youtube_api_key_3,
            self.youtube_api_key_4,
        ]
        return [k for k in keys if k and k.strip()]

    @property
    def gemini_api_keys(self) -> List[str]:
        """Return list of active non-empty Gemini API keys."""
        keys = [
            self.gemini_api_key_1,
            self.gemini_api_key_2,
            self.gemini_api_key_3,
            self.gemini_api_key_4,
        ]
        return [k for k in keys if k and k.strip()]

    @property
    def is_database_configured(self) -> bool:
        """Check if a valid database URL is provided."""
        return bool(self.database_url and self.database_url.strip())

    @property
    def is_redis_configured(self) -> bool:
        """Check if a valid Redis URL is provided."""
        return bool(self.redis_url and self.redis_url.strip())

    @property
    def is_youtube_configured(self) -> bool:
        """Check if at least one YouTube API key is provided."""
        return len(self.youtube_api_keys) > 0

    @property
    def is_gemini_configured(self) -> bool:
        """Check if at least one Gemini API key is provided."""
        return len(self.gemini_api_keys) > 0


# Cached global settings instance
settings = Settings()
