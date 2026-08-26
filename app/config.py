"""Application configuration using Pydantic Settings."""

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils import get_logger

logger = get_logger("goddess.config")


class ChannelConfig(BaseModel):
    """Configuration for a single YouTube channel."""

    channel_id: str = Field(..., description="YouTube Channel ID, e.g. UCxxxxxxxx")
    enabled: bool = Field(default=True, description="Whether bot is active on this channel")
    name: str = Field(default="Stream Channel", description="Descriptive name")


class Settings(BaseSettings):
    """Global application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/goddess_ai",
        description="Async PostgreSQL connection string",
    )

    # Web Server & Deployment
    PORT: int = Field(default=8000, description="Port to listen on")
    ENVIRONMENT: str = Field(default="production", description="Environment: production/development/test")

    # 4 Gemini API Keys
    GEMINI_API_KEY_1: str | None = Field(default=None)
    GEMINI_API_KEY_2: str | None = Field(default=None)
    GEMINI_API_KEY_3: str | None = Field(default=None)
    GEMINI_API_KEY_4: str | None = Field(default=None)

    # 3 YouTube Data API Keys (Read-only)
    YOUTUBE_API_KEY_1: str | None = Field(default=None)
    YOUTUBE_API_KEY_2: str | None = Field(default=None)
    YOUTUBE_API_KEY_3: str | None = Field(default=None)

    # Google OAuth 2.0 (For authenticated write operations)
    GOOGLE_CLIENT_ID: str | None = Field(default=None)
    GOOGLE_CLIENT_SECRET: str | None = Field(default=None)
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/oauth2callback")

    YOUTUBE_OAUTH_TOKEN: str | None = Field(default=None)
    YOUTUBE_OAUTH_REFRESH_TOKEN: str | None = Field(default=None)

    # WebSub Stream Detection
    WEBSUB_CALLBACK_URL: str | None = Field(default=None)
    WEBSUB_SECRET: str = Field(default="goddess-ai-websub-secret")

    # Optional Notifications (Discord Webhook for HITL / Alerts)
    DISCORD_MOD_WEBHOOK_URL: str | None = Field(default=None)

    # Path to channels configuration
    CHANNELS_FILE: str = Field(default="channels.json")

    # Cooldown & Threshold Defaults
    DEFAULT_XP_PER_MESSAGE: int = 10
    DEFAULT_COINS_PER_MESSAGE: int = 5
    DEFAULT_REWARD_COOLDOWN_SECONDS: int = 60
    DEFAULT_COHOST_COOLDOWN_SECONDS: int = 10
    DEFAULT_MODERATION_THRESHOLD: float = 0.90
    DEFAULT_HITL_THRESHOLD: float = 0.40
    CONTEXT_MESSAGE_COUNT: int = 10

    def get_gemini_keys(self) -> list[str]:
        """Return non-empty Gemini API keys."""
        keys = [
            self.GEMINI_API_KEY_1,
            self.GEMINI_API_KEY_2,
            self.GEMINI_API_KEY_3,
            self.GEMINI_API_KEY_4,
        ]
        return [k.strip() for k in keys if k and k.strip()]

    def get_youtube_keys(self) -> list[str]:
        """Return non-empty YouTube Data API keys."""
        keys = [
            self.YOUTUBE_API_KEY_1,
            self.YOUTUBE_API_KEY_2,
            self.YOUTUBE_API_KEY_3,
        ]
        return [k.strip() for k in keys if k and k.strip()]

    def load_channels(self) -> list[ChannelConfig]:
        """Load, validate, deduplicate, and filter channels from channels.json."""
        path = Path(self.CHANNELS_FILE)
        if not path.exists():
            logger.warning(f"Channels file {self.CHANNELS_FILE} not found. Using empty channel list.")
            return []

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            raw_channels = []
            if isinstance(data, list):
                raw_channels = data
            elif isinstance(data, dict) and "channels" in data:
                raw_channels = data["channels"]
            else:
                logger.error(
                    f"Invalid format in {self.CHANNELS_FILE}. Expected list or object with 'channels' key."
                )
                return []

            seen_ids: set[str] = set()
            valid_channels: list[ChannelConfig] = []

            for item in raw_channels:
                try:
                    ch = ChannelConfig(**item)
                    if not ch.channel_id.strip():
                        continue
                    clean_id = ch.channel_id.strip()
                    if clean_id in seen_ids:
                        logger.debug(f"Skipping duplicate channel ID: {clean_id}")
                        continue
                    seen_ids.add(clean_id)
                    if ch.enabled:
                        valid_channels.append(ch)
                    else:
                        logger.info(f"Channel {clean_id} ({ch.name}) is disabled. Skipping.")
                except Exception as e:
                    logger.warning(f"Error parsing channel config entry {item}: {e}")

            logger.info(f"Loaded {len(valid_channels)} enabled channel(s) from {self.CHANNELS_FILE}")
            return valid_channels

        except Exception as e:
            logger.error(f"Failed to read channels file {self.CHANNELS_FILE}: {e}")
            return []

    def log_summary(self) -> None:
        """Log sanitized configuration summary."""
        gemini_count = len(self.get_gemini_keys())
        yt_count = len(self.get_youtube_keys())
        has_oauth = bool(self.YOUTUBE_OAUTH_REFRESH_TOKEN or self.YOUTUBE_OAUTH_TOKEN)
        logger.info(
            f"Config initialized: GeminiKeys={gemini_count} YouTubeKeys={yt_count} "
            f"OAuthConfigured={has_oauth} "
            f"WebSubCallback={self.WEBSUB_CALLBACK_URL or '[NOT_SET]'}"
        )


settings = Settings()
