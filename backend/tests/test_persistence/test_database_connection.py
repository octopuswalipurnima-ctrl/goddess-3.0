"""
Tests for database engine, normalization, and connection health diagnostics.
"""

import pytest
from sqlalchemy import text
from app.db.session import (
    get_engine,
    normalize_database_url,
    ping_database,
)


def test_normalize_database_url():
    """Test dialect normalization for PostgreSQL and SQLite URLs."""
    assert normalize_database_url("postgresql://user:pass@localhost:5432/db") == "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert normalize_database_url("postgres://user:pass@localhost:5432/db") == "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert normalize_database_url("sqlite:///local.db") == "sqlite+aiosqlite:///local.db"
    assert normalize_database_url(None) is None
    assert normalize_database_url("") is None


@pytest.mark.asyncio
async def test_database_connection_and_query(test_db_engine):
    """Verify executing async SQL query on the initialized engine."""
    async with test_db_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS num"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1


@pytest.mark.asyncio
async def test_ping_database_unconfigured(monkeypatch):
    """Verify ping_database reports NOT_CONFIGURED when no URL is provided."""
    monkeypatch.setattr("app.db.session.get_engine", lambda: None)
    res = await ping_database()
    assert res["status"] == "NOT_CONFIGURED"
    assert res["latency_ms"] is None
