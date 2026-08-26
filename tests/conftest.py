"""Pytest fixtures for Goddess AI 3.0 test suite."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.database as db_module
from app.database import Base
from app.models import Channel, ChannelSettings, Stream


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite database engine for testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch global engine in db_module
    old_engine = db_module.engine
    old_factory = db_module.async_session_factory
    db_module.engine = test_engine
    db_module.async_session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
    db_module.engine = old_engine
    db_module.async_session_factory = old_factory


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean AsyncSession per test."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def setup_channel_and_stream(
    db_session: AsyncSession,
) -> tuple[Channel, ChannelSettings, Stream]:
    """Seed test database with an active channel, settings, and live stream."""
    channel = Channel(
        channel_id="UC_TEST_CHANNEL_1",
        name="Test Channel",
        enabled=True,
    )
    db_session.add(channel)
    await db_session.flush()

    settings_obj = ChannelSettings(
        channel_id="UC_TEST_CHANNEL_1",
        ai_enabled=True,
        cohost_enabled=True,
        moderation_enabled=True,
        moderation_mode="balanced",
        moderation_threshold=0.90,
        personality="friendly",
        xp_per_message=10,
        coins_per_message=5,
        reward_cooldown=60,
    )
    db_session.add(settings_obj)

    stream = Stream(
        channel_id="UC_TEST_CHANNEL_1",
        youtube_video_id="TEST_VIDEO_1",
        live_chat_id="TEST_LIVE_CHAT_1",
        title="Test Live Stream",
        status="LIVE",
    )
    db_session.add(stream)
    await db_session.commit()

    return channel, settings_obj, stream
