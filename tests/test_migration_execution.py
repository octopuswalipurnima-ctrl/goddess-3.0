"""Tests for Alembic migration execution, table creation, and schema integrity."""

import asyncio
import os
import time

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.database import close_engine, init_engine, verify_database_schema


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

            # Verify streams columns including join_message_sent
            stream_cols_res = await conn.execute(text("PRAGMA table_info(streams);"))
            stream_cols = {row[1] for row in stream_cols_res.fetchall()}
            assert "join_message_sent" in stream_cols
            assert "youtube_video_id" in stream_cols
            assert "live_chat_id" in stream_cols
            assert "status" in stream_cols

        await engine.dispose()

    asyncio.run(verify_tables())


def test_migration_001_to_002_step_upgrade(tmp_path):
    """Test upgrading from 001_initial_schema to 002_add_join_message_sent preserves existing rows."""
    db_file = tmp_path / "test_step_migration.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    os.environ["DATABASE_URL"] = db_url
    os.environ["APP_ENV"] = "test"

    alembic_cfg = Config("alembic.ini")

    # 1. Upgrade to 001
    command.upgrade(alembic_cfg, "001_initial_schema")

    async def insert_test_stream():
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO streams (channel_id, youtube_video_id, live_chat_id, title, status) "
                    "VALUES ('UC_TEST', 'VID_123', 'CHAT_123', 'Test Stream', 'LIVE')"
                )
            )
            await conn.commit()
        await engine.dispose()

    asyncio.run(insert_test_stream())

    # 2. Upgrade to 002
    command.upgrade(alembic_cfg, "002_add_join_message_sent")

    async def verify_after_upgrade():
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(
                text(
                    "SELECT id, channel_id, youtube_video_id, join_message_sent FROM streams WHERE youtube_video_id='VID_123'"
                )
            )
            row = res.fetchone()
            assert row is not None
            assert row[1] == "UC_TEST"
            assert row[2] == "VID_123"
            # In SQLite / Postgres, default is False (0)
            assert bool(row[3]) is False
        await engine.dispose()

    asyncio.run(verify_after_upgrade())


@pytest.mark.asyncio
async def test_schema_integrity_verifier():
    """Verify verify_database_schema returns True on standard test database."""
    init_engine()
    ok, missing = await verify_database_schema()
    assert ok is True
    assert len(missing) == 0
    await close_engine()
