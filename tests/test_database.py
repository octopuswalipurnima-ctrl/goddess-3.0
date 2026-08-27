"""Tests for database URL normalization, password masking, environment-aware validation, and connectivity checks."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

import app.database as db_module
from app.config import Settings, normalize_database_url
from app.database import verify_database_connection
from app.main import app
from app.utils import mask_database_url


def test_database_url_normalization():
    """Test URL normalization for all supported dialects."""
    # 1. postgresql:// -> postgresql+asyncpg://
    assert (
        normalize_database_url("postgresql://postgres:secret@host.internal:5432/db")
        == "postgresql+asyncpg://postgres:secret@host.internal:5432/db"
    )

    # 2. postgres:// -> postgresql+asyncpg:// (Heroku / Railway legacy style)
    assert (
        normalize_database_url("postgres://postgres:secret@host.internal:5432/db")
        == "postgresql+asyncpg://postgres:secret@host.internal:5432/db"
    )

    # 3. postgresql+asyncpg:// -> preserved as-is
    assert (
        normalize_database_url("postgresql+asyncpg://postgres:secret@host.internal:5432/db")
        == "postgresql+asyncpg://postgres:secret@host.internal:5432/db"
    )

    # 4. sqlite:// -> sqlite+aiosqlite://
    assert normalize_database_url("sqlite:///data.db") == "sqlite+aiosqlite:///data.db"

    # 5. sqlite+aiosqlite:// -> preserved as-is
    assert normalize_database_url("sqlite+aiosqlite:///:memory:") == "sqlite+aiosqlite:///:memory:"

    # 6. Empty / None URL handling
    assert normalize_database_url("") == ""
    assert normalize_database_url(None) == ""


def test_database_url_query_parameter_preservation():
    """Test that query parameters such as sslmode, application_name are preserved intact."""
    url = (
        "postgres://user:pass@host.railway.internal:5432/railway?sslmode=require&application_name=goddess_ai"
    )
    normalized = normalize_database_url(url)
    assert (
        normalized
        == "postgresql+asyncpg://user:pass@host.railway.internal:5432/railway?sslmode=require&application_name=goddess_ai"
    )


def test_database_url_special_character_passwords():
    """Test that special character passwords (e.g. @, %, !) in URLs are not corrupted."""
    url = "postgres://db_user:p%40ss%3Aword%21@postgres.railway.internal:5432/db"
    normalized = normalize_database_url(url)
    assert normalized == "postgresql+asyncpg://db_user:p%40ss%3Aword%21@postgres.railway.internal:5432/db"


def test_database_url_password_masking():
    """Test that mask_database_url never leaks passwords in diagnostics or logs."""
    url = (
        "postgresql+asyncpg://db_user:super_secret_password_123@postgres.railway.internal:5432/production_db"
    )
    masked = mask_database_url(url)

    assert masked["driver"] == "postgresql+asyncpg"
    assert masked["host"] == "postgres.railway.internal"
    assert masked["port"] == "5432"
    assert masked["database"] == "production_db"
    assert masked["user"] == "db_user"

    # Password must NEVER appear in the summary
    assert "super_secret_password_123" not in masked["safe_summary"]
    assert "db=production_db" in masked["safe_summary"]
    assert "host=postgres.railway.internal:5432" in masked["safe_summary"]


def test_production_without_database_url_raises_error():
    """Test that missing DATABASE_URL in production raises a clear, actionable error."""
    prod_settings = Settings(
        DATABASE_URL=None,
        POSTGRES_URL=None,
        DATABASE_PUBLIC_URL=None,
        APP_ENV="production",
    )

    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        prod_settings.get_database_url()


def test_localhost_rejection_in_production():
    """Test that localhost/127.0.0.1 database URL in production is strictly rejected."""
    prod_settings = Settings(
        DATABASE_URL="postgresql://postgres:pass@localhost:5432/goddess_ai",
        APP_ENV="production",
    )

    with pytest.raises(ValueError, match="Unsafe database host 'localhost' detected in production"):
        prod_settings.get_database_url()

    prod_settings_ip = Settings(
        DATABASE_URL="postgresql://postgres:pass@127.0.0.1:5432/goddess_ai",
        APP_ENV="production",
    )

    with pytest.raises(ValueError, match="Unsafe database host '127.0.0.1' detected in production"):
        prod_settings_ip.get_database_url()


def test_development_fallback():
    """Test that missing DATABASE_URL in development allows local development fallback."""
    dev_settings = Settings(
        DATABASE_URL=None,
        POSTGRES_URL=None,
        DATABASE_PUBLIC_URL=None,
        APP_ENV="development",
    )

    url = dev_settings.get_database_url()
    assert "localhost:5432" in url
    assert url.startswith("postgresql+asyncpg://")


def test_development_explicit_postgresql_url():
    """Test development environment with explicit cloud PostgreSQL connection."""
    dev_settings = Settings(
        DATABASE_URL="postgresql://user:pass@remote.host:5432/dev_db",
        APP_ENV="development",
    )

    url = dev_settings.get_database_url()
    assert url == "postgresql+asyncpg://user:pass@remote.host:5432/dev_db"


def test_railway_postgres_url_fallback():
    """Test that POSTGRES_URL or DATABASE_PUBLIC_URL is used if DATABASE_URL is not set."""
    railway_settings = Settings(
        DATABASE_URL=None,
        POSTGRES_URL="postgresql://postgres:pw@postgres.railway.internal:5432/railway",
        APP_ENV="production",
    )

    url = railway_settings.get_database_url()
    assert url == "postgresql+asyncpg://postgres:pw@postgres.railway.internal:5432/railway"


def test_alembic_db_url_resolution():
    """Test that Alembic can resolve the runtime database URL."""
    test_settings = Settings(
        DATABASE_URL="postgresql://postgres:pw@postgres.railway.internal:5432/railway",
        APP_ENV="production",
    )
    assert (
        test_settings.get_database_url()
        == "postgresql+asyncpg://postgres:pw@postgres.railway.internal:5432/railway"
    )


@pytest.mark.asyncio
async def test_database_connectivity_success():
    """Test successful database connection test with SELECT 1."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    old_engine = db_module.engine
    db_module.engine = test_engine

    try:
        ok, diag = await verify_database_connection(timeout_seconds=2.0)
        assert ok is True
        assert "connected" in diag.lower()
    finally:
        await test_engine.dispose()
        db_module.engine = old_engine


@pytest.mark.asyncio
async def test_database_connectivity_failure_sanitized():
    """Test that connection failures produce sanitized diagnostics without crashes."""
    unreachable_engine = create_async_engine(
        "sqlite+aiosqlite:////invalid/path/that/cannot/exist/db.sqlite",
        echo=False,
    )
    old_engine = db_module.engine
    db_module.engine = unreachable_engine

    try:
        ok, diag = await verify_database_connection(timeout_seconds=1.0)
        assert ok is False
        assert isinstance(diag, str)
        assert len(diag) > 0
    finally:
        await unreachable_engine.dispose()
        db_module.engine = old_engine


@pytest.mark.asyncio
async def test_health_live_endpoint():
    """Test that /health/live returns immediate HTTP 200 without database calls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "live"}


@pytest.mark.asyncio
async def test_health_endpoint_database_status():
    """Test that /health returns database status without exposing credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "database" in data
        assert isinstance(data["database"], dict)
        assert "configured" in data["database"]
        assert "connected" in data["database"]
