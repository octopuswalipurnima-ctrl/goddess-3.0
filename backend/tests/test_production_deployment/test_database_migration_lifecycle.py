"""
Tests for Database Migration Lifecycle and Determinism in GODDESS AI 2.0.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from app.db.base import Base


@pytest.mark.asyncio
async def test_database_schema_creation_and_idempotent_startup():
    """Verify database schema creates all tables idempotently without corruption."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Query database
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Re-running create_all must be idempotent
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_database_table_presence_audit():
    """Verify core domain tables exist in metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "stream_configs",
        "moderation_audit_records",
        "cohost_audit_records",
        "cohost_configs",
        "module_configs",
        "creator_settings",
        "users",
    }
    for t in expected_tables:
        assert t in table_names, f"Table '{t}' missing from Base metadata."
