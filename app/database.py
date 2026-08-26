"""Database initialization, SQLAlchemy async engine, and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.utils import get_logger

logger = get_logger("goddess.database")


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""


# Global engine and sessionmaker
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_db_url() -> str:
    """Ensure proper async dialect in DB URL."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def init_engine(db_url: str | None = None) -> AsyncEngine:
    """Initialize the global async engine and session factory."""
    global engine, async_session_factory
    target_url = db_url or get_db_url()

    # Configure connection pool settings based on dialect
    kwargs: dict[str, Any] = {}
    if "sqlite" in target_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True

    engine = create_async_engine(target_url, echo=False, **kwargs)
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    logger.info("Database engine initialized.")
    return engine


async def close_engine() -> None:
    """Gracefully dispose of the database engine."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Database engine closed.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session context manager."""
    global async_session_factory
    if async_session_factory is None:
        init_engine()
    assert async_session_factory is not None

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining a database session."""
    async with get_session() as session:
        yield session
