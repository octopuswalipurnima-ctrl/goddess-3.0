"""Application configuration using Pydantic Settings with hardened database resolution."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils import get_logger, mask_database_url

logger = get_logger("goddess.config")


def normalize_database_url(raw_url: str | None) -> str:
    """
    Ensure proper async dialect in database URL without corrupting query parameters,
    special character passwords, or SSL options.
    Converts:
        postgres://...   -> postgresql+asyncpg://...
        postgresql://... -> postgresql+asyncpg://...
        sqlite://...     -> sqlite+aiosqlite://...
    Preserves:
        postgresql+asyncpg://... -> untouched
        sqlite+aiosqlite://...   -> untouched
    """
    if not raw_url or not raw_url.strip():
        return ""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    return url


class ChannelConfig(BaseModel):
    """Configuration for a single YouTube channel."""

    channel_id: str = Field(..., description="YouTube Channel ID, e.g. UCxxxxxxxx")
    enabled: bool = Field(default=True, description="Whether bot is active on this channel")
    name: str = Field(default="Stream Channel", description="Descriptive name")
    auto_join: bool = Field(
        default=True, description="Whether bot automatically sends join message upon stream start"
    )


class Settings(BaseSettings):
    """Global application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database URLs (supports standard DATABASE_URL as well as Railway-provided fallbacks)
    DATABASE_URL: str | None = Field(
        default=None,
        description="Primary async PostgreSQL connection string",
    )
    POSTGRES_URL: str | None = Field(
        default=None,
        description="Railway alternative Postgres connection variable",
    )
    DATABASE_PUBLIC_URL: str | None = Field(
        default=None,
        description="Railway public Postgres connection fallback",
    )
    POSTGRESQL_URL: str | None = Field(
        default=None,
        description="PostgreSQL fallback connection variable",
    )

    # Environment (supports both APP_ENV and ENVIRONMENT)
    APP_ENV: str | None = Field(
        default=None, description="Application environment: production/development/test"
    )
    ENVIRONMENT: str = Field(default="production", description="Fallback environment variable")
    PORT: int = Field(default=8000, description="Port to listen on")

    # Gemini API Keys
    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_API_KEY_1: str | None = Field(default=None)
    GEMINI_API_KEY_2: str | None = Field(default=None)
    GEMINI_API_KEY_3: str | None = Field(default=None)
    GEMINI_API_KEY_4: str | None = Field(default=None)
    GEMINI_API_KEY_5: str | None = Field(default=None)
    GEMINI_API_KEY_6: str | None = Field(default=None)
    GEMINI_API_KEY_7: str | None = Field(default=None)
    GEMINI_API_KEY_8: str | None = Field(default=None)
    GEMINI_API_KEY_9: str | None = Field(default=None)
    GEMINI_API_KEY_10: str | None = Field(default=None)
    GEMINI_API_KEYS: str | None = Field(default=None)

    # YouTube Data API Keys (Read-only pool, supports multiple keys for quota rotation)
    YOUTUBE_API_KEY: str | None = Field(default=None)
    YOUTUBE_API_KEY_1: str | None = Field(default=None)
    YOUTUBE_API_KEY_2: str | None = Field(default=None)
    YOUTUBE_API_KEY_3: str | None = Field(default=None)
    YOUTUBE_API_KEY_4: str | None = Field(default=None)
    YOUTUBE_API_KEY_5: str | None = Field(default=None)
    YOUTUBE_API_KEY_6: str | None = Field(default=None)
    YOUTUBE_API_KEY_7: str | None = Field(default=None)
    YOUTUBE_API_KEY_8: str | None = Field(default=None)
    YOUTUBE_API_KEY_9: str | None = Field(default=None)
    YOUTUBE_API_KEY_10: str | None = Field(default=None)
    YOUTUBE_API_KEYS: str | None = Field(default=None)

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

    # Joining Greeting Message
    JOIN_MESSAGE: str = Field(
        default="🍯 Honney is here! 👋 Have an awesome stream! 💜",
        description="Greeting message sent once when bot connects to a live stream",
    )

    # Cooldown & Threshold Defaults
    DEFAULT_XP_PER_MESSAGE: int = 10
    DEFAULT_COINS_PER_MESSAGE: int = 5
    DEFAULT_REWARD_COOLDOWN_SECONDS: int = 60
    DEFAULT_COHOST_COOLDOWN_SECONDS: int = 10
    DEFAULT_MODERATION_THRESHOLD: float = 0.90
    DEFAULT_HITL_THRESHOLD: float = 0.40
    CONTEXT_MESSAGE_COUNT: int = 10

    @property
    def env_name(self) -> str:
        """Normalized environment name dynamically checking os.environ."""
        import os

        return (
            (
                os.environ.get("APP_ENV")
                or self.APP_ENV
                or os.environ.get("ENVIRONMENT")
                or self.ENVIRONMENT
                or "production"
            )
            .strip()
            .lower()
        )

    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.env_name in ("production", "prod") or self.env_name not in ("development", "dev", "test")

    @property
    def is_development(self) -> bool:
        """Check if environment is local development."""
        return self.env_name in ("development", "dev")

    @property
    def is_test(self) -> bool:
        """Check if environment is automated test."""
        return self.env_name == "test"

    def get_database_url_safe(self) -> str | None:
        """Retrieve database URL candidate dynamically checking instance attributes and os.environ."""
        import os

        candidates = [
            self.DATABASE_URL,
            os.environ.get("DATABASE_URL"),
            self.POSTGRES_URL,
            os.environ.get("POSTGRES_URL"),
            self.DATABASE_PUBLIC_URL,
            os.environ.get("DATABASE_PUBLIC_URL"),
            self.POSTGRESQL_URL,
            os.environ.get("POSTGRESQL_URL"),
        ]
        for c in candidates:
            if c and c.strip():
                return normalize_database_url(c.strip())
        return None

    def get_database_url(self) -> str:
        """
        Resolve, normalize, and validate the database URL based on environment.
        In production:
          - Requires DATABASE_URL from environment.
          - Rejects unsafe localhost/127.0.0.1 addresses.
          - Raises clear, actionable error if missing.
        In development:
          - Allows explicit local development fallback with warning.
        In test:
          - Allows in-memory test database.
        """
        candidate = self.get_database_url_safe()
        if candidate:
            # If in production, ensure no accidental localhost connection
            if self.is_production:
                masked = mask_database_url(candidate)
                host_lower = masked.get("host", "").lower()
                if host_lower in ("localhost", "127.0.0.1", "::1"):
                    raise ValueError(
                        f"Unsafe database host '{host_lower}' detected in production environment. "
                        "Production must connect to the configured cloud database (e.g. Railway PostgreSQL)."
                    )
            return candidate

        # No DATABASE_URL found in environment variables
        if self.is_development:
            logger.warning(
                "No DATABASE_URL found in environment variables. "
                "Using local development fallback at localhost:5432 (APP_ENV=development)."
            )
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/goddess_ai"

        if self.is_test:
            return "sqlite+aiosqlite:///:memory:"

        # In production: strict validation failure
        raise ValueError(
            "DATABASE_URL is not configured. "
            "In Railway: ensure a PostgreSQL database service exists in your project and "
            "link the variable DATABASE_URL=${{Postgres.DATABASE_URL}} in your service settings."
        )

    def get_gemini_keys(self) -> list[str]:
        """Return non-empty Gemini API keys checking instance attributes, os.environ, and comma-separated lists."""
        import os

        keys: list[str] = []

        # 1. Comma/newline separated GEMINI_API_KEYS
        multi = os.environ.get("GEMINI_API_KEYS") or self.GEMINI_API_KEYS
        if multi:
            for part in multi.replace("\n", ",").split(","):
                if part.strip():
                    keys.append(part.strip())

        # 2. Singular GEMINI_API_KEY
        single = os.environ.get("GEMINI_API_KEY") or self.GEMINI_API_KEY
        if single and single.strip():
            keys.append(single.strip())

        # 3. Explicit slots 1 to 10
        for i in range(1, 11):
            var_name = f"GEMINI_API_KEY_{i}"
            val = os.environ.get(var_name) or getattr(self, var_name, None)
            if val and val.strip():
                keys.append(val.strip())

        # 4. Any dynamic GEMINI_API_KEY_* in environment
        for k, v in os.environ.items():
            if (
                (k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_KEY_"))
                and v
                and v.strip()
                and v.strip() not in keys
            ):
                keys.append(v.strip())

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                deduped.append(k)
        return deduped

    def get_youtube_keys(self) -> list[str]:
        """Return non-empty YouTube Data API keys checking instance attributes, os.environ, and comma-separated lists."""
        import os

        keys: list[str] = []

        # 1. Comma/newline separated YOUTUBE_API_KEYS
        multi = os.environ.get("YOUTUBE_API_KEYS") or self.YOUTUBE_API_KEYS
        if multi:
            for part in multi.replace("\n", ",").split(","):
                if part.strip():
                    keys.append(part.strip())

        # 2. Singular YOUTUBE_API_KEY
        single = os.environ.get("YOUTUBE_API_KEY") or self.YOUTUBE_API_KEY
        if single and single.strip():
            keys.append(single.strip())

        # 3. Explicit slots 1 to 10
        for i in range(1, 11):
            var_name = f"YOUTUBE_API_KEY_{i}"
            val = os.environ.get(var_name) or getattr(self, var_name, None)
            if val and val.strip():
                keys.append(val.strip())

        # 4. Any dynamic YOUTUBE_API_KEY_* or YOUTUBE_KEY_* in environment
        for k, v in os.environ.items():
            if (
                (k.startswith("YOUTUBE_API_KEY_") or k.startswith("YOUTUBE_KEY_"))
                and v
                and v.strip()
                and v.strip() not in keys
            ):
                keys.append(v.strip())

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                deduped.append(k)
        return deduped

    def get_youtube_key_slot_diagnostics(self) -> list[dict[str, Any]]:
        """Return safe slot-by-slot presence report without revealing credentials."""
        import os

        slots: list[tuple[str, str | None]] = []
        # Check standard slots 1 through 10
        for i in range(1, 11):
            var_name = f"YOUTUBE_API_KEY_{i}"
            val = os.environ.get(var_name) or getattr(self, var_name, None)
            clean = val.strip() if val else None
            present = bool(clean)
            if present or i <= 4:  # always report at least slots 1-4, and any other slot that is present
                slots.append((f"Key #{i} ({var_name})", clean))

        if os.environ.get("YOUTUBE_API_KEY") or self.YOUTUBE_API_KEY:
            single_val = os.environ.get("YOUTUBE_API_KEY") or self.YOUTUBE_API_KEY
            slots.append(("Singular (YOUTUBE_API_KEY)", single_val.strip() if single_val else None))

        report = []
        for name, clean in slots:
            present = bool(clean)
            length = len(clean) if clean else 0
            report.append(
                {
                    "slot": name,
                    "present": present,
                    "status": "PRESENT" if present else "MISSING",
                    "length": length,
                }
            )
        return report

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
        """Log sanitized configuration summary without leaking passwords or secrets."""
        gemini_count = len(self.get_gemini_keys())
        yt_count = len(self.get_youtube_keys())
        has_oauth = bool(self.YOUTUBE_OAUTH_REFRESH_TOKEN or self.YOUTUBE_OAUTH_TOKEN)
        db_safe = mask_database_url(self.get_database_url_safe())

        logger.info(
            f"Config initialized: Env={self.env_name} "
            f"Database=[{db_safe['safe_summary']}] "
            f"GeminiKeys={gemini_count} YouTubeKeys={yt_count} "
            f"OAuthConfigured={has_oauth} "
            f"WebSubCallback={self.WEBSUB_CALLBACK_URL or '[NOT_SET]'}"
        )
        for slot_info in self.get_youtube_key_slot_diagnostics():
            logger.info(f"  {slot_info['slot']}: {slot_info['status']} (length={slot_info['length']})")


settings = Settings()
