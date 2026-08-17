"""
Production Configuration Validator for GODDESS AI 2.0.

Validates environment configuration, secrets, database/Redis URLs, CORS settings,
and security parameters before the application accepts live production traffic.
Enforces strict FAIL-CLOSED policy in production while permitting safe defaults in development.
Never prints, logs, or returns sensitive credential values.
"""

from typing import Any, Dict, List, Tuple
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("core.validator")

# Known insecure placeholder patterns that MUST NOT be used in production
INSECURE_PLACEHOLDER_SUBSTRINGS = [
    "insecure",
    "changeme",
    "change-me",
    "development",
    "placeholder",
    "default",
    "secret123",
    "testkey",
]


class ConfigurationValidationError(RuntimeError):
    """Raised when production configuration fails safety validation."""
    pass


def get_safe_configuration_summary(settings: Settings) -> Dict[str, str]:
    """
    Generate safe diagnostic output for system logging and health reporting
    with guaranteed ZERO raw secret values.
    """
    yt_count = len(settings.youtube_api_keys)
    gemini_count = len(settings.gemini_api_keys)

    sec_len = len(settings.secret_key.strip())
    sec_valid = sec_len >= 32 and not any(p in settings.secret_key.lower() for p in INSECURE_PLACEHOLDER_SUBSTRINGS)

    return {
        "ENVIRONMENT": settings.environment.upper(),
        "DATABASE": "CONFIGURED" if settings.is_database_configured else "NOT_CONFIGURED",
        "REDIS": "CONFIGURED" if settings.is_redis_configured else "NOT_CONFIGURED",
        "YOUTUBE": f"{yt_count} CREDENTIAL(S)" if yt_count > 0 else "NOT_CONFIGURED",
        "GEMINI": f"{gemini_count} CREDENTIAL(S)" if gemini_count > 0 else "NOT_CONFIGURED",
        "SECRET_KEY": "VALID (32+ chars)" if sec_valid else "INVALID_OR_WEAK",
        "JWT_ALGORITHM": settings.jwt_algorithm,
        "AUTH_MODE": "ENFORCED" if settings.auth_enabled else "DISABLED",
        "RATE_LIMITING": "ENFORCED" if settings.rate_limit_enabled else "DISABLED",
        "CORS_ORIGINS": f"{len(settings.cors_origins)} ORIGIN(S) DEFINED",
    }


def validate_production_configuration(settings: Settings) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate system configuration against production security policies.

    Returns:
        Tuple of (is_valid: bool, issues: List[str], diagnostics: Dict[str, Any])
    
    Raises:
        ConfigurationValidationError if environment is 'production' and any fatal issue is found.
    """
    issues: List[str] = []
    diagnostics: Dict[str, Any] = {
        "environment": settings.environment,
        "debug_mode": settings.debug,
        "auth_enabled": settings.auth_enabled,
        "auth_dev_bypass": settings.auth_dev_bypass,
        "rate_limiting_enabled": settings.rate_limit_enabled,
        "database_configured": settings.is_database_configured,
        "redis_configured": settings.is_redis_configured,
        "youtube_key_count": len(settings.youtube_api_keys),
        "gemini_key_count": len(settings.gemini_api_keys),
        "cors_origin_count": len(settings.cors_origins),
    }

    is_production = settings.environment.lower() == "production"

    # 1. Secret Key & JWT Validation
    secret_key = settings.secret_key.strip()
    if len(secret_key) < 32:
        issues.append("SECRET_KEY must be at least 32 characters in length.")
    
    secret_lower = secret_key.lower()
    for placeholder in INSECURE_PLACEHOLDER_SUBSTRINGS:
        if placeholder in secret_lower:
            issues.append(f"SECRET_KEY contains insecure pattern '{placeholder}'. Must be cryptographically generated.")
            break

    if settings.jwt_algorithm != "HS256":
        issues.append(f"JWT algorithm must be locked to 'HS256' (found: {settings.jwt_algorithm}).")

    if not settings.jwt_issuer or not settings.jwt_audience:
        issues.append("JWT issuer and audience must be explicitly configured.")

    # 2. Authentication & Bypass Guards
    if is_production:
        if not settings.auth_enabled:
            issues.append("AUTH_ENABLED must be True in production.")
        if settings.auth_dev_bypass:
            issues.append("AUTH_DEV_BYPASS is strictly prohibited in production.")
        if settings.debug:
            issues.append("DEBUG mode must be disabled (False) in production.")
        if not settings.rate_limit_enabled:
            issues.append("RATE_LIMIT_ENABLED must be True in production.")

    # 3. Database URL Validation
    if is_production:
        if not settings.is_database_configured:
            issues.append("DATABASE_URL is required in production (PostgreSQL asyncpg).")
        elif settings.database_url:
            db_url = settings.database_url.lower()
            if "sqlite" in db_url or ":memory:" in db_url:
                issues.append("SQLite / in-memory database is prohibited in production. Use PostgreSQL.")
            elif not db_url.startswith("postgresql+asyncpg://") and not db_url.startswith("postgresql://") and not db_url.startswith("postgres://"):
                issues.append("DATABASE_URL must be a valid PostgreSQL connection string.")

    # 4. Redis URL Validation (if configured)
    if settings.redis_url:
        r_url = settings.redis_url.lower()
        if not r_url.startswith("redis://") and not r_url.startswith("rediss://"):
            issues.append("REDIS_URL must use redis:// or rediss:// protocol.")

    # 5. YouTube API Credentials
    if is_production:
        if not settings.is_youtube_configured:
            issues.append("At least one valid YouTube API key is required in production.")
        else:
            for idx, key in enumerate(settings.youtube_api_keys, 1):
                if any(p in key.lower() for p in ["placeholder", "dummy", "fake", "example"]):
                    issues.append(f"YouTube API Key #{idx} appears to be a placeholder.")
                if len(key) < 20:
                    issues.append(f"YouTube API Key #{idx} is suspiciously short ({len(key)} chars).")

    # 6. Gemini AI Credentials
    if is_production:
        if not settings.is_gemini_configured:
            issues.append("At least one valid Gemini API key is required in production.")
        else:
            for idx, key in enumerate(settings.gemini_api_keys, 1):
                if any(p in key.lower() for p in ["placeholder", "dummy", "fake", "example"]):
                    issues.append(f"Gemini API Key #{idx} appears to be a placeholder.")
                if len(key) < 20:
                    issues.append(f"Gemini API Key #{idx} is suspiciously short ({len(key)} chars).")

    # 7. CORS Configuration Validation
    if is_production:
        if not settings.cors_origins or len(settings.cors_origins) == 0:
            issues.append("CORS_ORIGINS must be configured with explicit creator dashboard origins.")
        for origin in settings.cors_origins:
            if origin == "*":
                issues.append("Wildcard CORS ('*') is prohibited in production when credentials are enabled.")
            elif not origin.startswith("http://") and not origin.startswith("https://"):
                issues.append(f"CORS origin '{origin}' is invalid. Must include http:// or https:// scheme.")

    # Summary
    is_valid = len(issues) == 0
    diagnostics["is_valid"] = is_valid
    diagnostics["issue_count"] = len(issues)
    diagnostics["issues"] = issues
    diagnostics["safe_summary"] = get_safe_configuration_summary(settings)

    if not is_valid:
        if is_production:
            logger.critical(f"FATAL: Production configuration failed validation with {len(issues)} errors: {issues}")
            raise ConfigurationValidationError(
                f"Production configuration validation failed with {len(issues)} safety violation(s): "
                + "; ".join(issues)
            )
        else:
            logger.warning(f"Development configuration notice ({len(issues)} items): {'; '.join(issues)}")

    return is_valid, issues, diagnostics
