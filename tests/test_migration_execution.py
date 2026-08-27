"""Tests for Alembic migration execution, table creation, and schema integrity."""

import os
import time

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command


def test_alembic_upgrade_head_execution(tmp_path):
    """Test that alembic upgrade head executes cleanly and creates all 13 tables."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    os.environ["DATABASE_URL"] = db_url
    os.environ["APP_ENV"] = "test"

    alembic_cfg = Config("alembic.ini")

    start_time = time.time()
    # Run migration
    command.upgrade(alembic_cfg, "head")
    duration = time.time() - start_time

    assert duration < 10.0  # Migration must complete in seconds

    # Verify all 13 tables exist in the database
    import asyncio

    async def verify_tables():
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = {row[0] for row in result.fetchall()}
            expected_tables = {
                "alembic_version",
                "channels",
                "channel_settings",
                "users",
                "streams",
                "chat_messages",
                "commands",
                "store_items",
                "purchases",
                "one_v_one_queue",
                "moderation_reviews",
                "moderation_memory",
                "websub_subscriptions",
                "audit_logs",
            }
            for table in expected_tables:
                assert table in tables, f"Expected table '{table}' was not created by migration!"
        await engine.dispose()

    asyncio.run(verify_tables())
