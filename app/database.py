"""Database initialization, SQLAlchemy async engine, session management, and connectivity verification."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.utils import get_logger, mask_database_url

logger = get_logger("goddess.database")


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""

    pass


# Global engine and sessionmaker singletons
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_db_url() -> str:
    """Ensure proper async dialect and environment-aware validation."""
    return settings.get_database_url()


def init_engine(db_url: str | None = None) -> AsyncEngine:
    """Initialize the global async engine and session factory."""
    global engine, async_session_factory
    target_url = db_url or get_db_url()
    safe_info = mask_database_url(target_url)

    # Configure connection pool settings based on dialect
    kwargs: dict[str, Any] = {}
    if "sqlite" in target_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 300

    engine = create_async_engine(target_url, echo=False, **kwargs)
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    logger.info(f"Database engine initialized: {safe_info['safe_summary']}")
    return engine


async def verify_database_connection(timeout_seconds: float = 5.0) -> tuple[bool, str]:
    """
    Test database connectivity with SELECT 1 and return a sanitized diagnostic message.
    Never exposes passwords, tokens, or sensitive credentials in error logs or return values.
    """
    global engine
    if engine is None:
        return False, "Database engine is not initialized."

    safe_info = mask_database_url(settings.get_database_url_safe())
    safe_host = f"{safe_info['host']}:{safe_info['port']}"

    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        # Formatted readiness report
        logger.info(f"DATABASE\n  URL: configured\n  Driver: {safe_info['driver']}\n  Connection: READY")
        return True, f"Database connected ({safe_info['safe_summary']})"
    except TimeoutError:
        msg = f"Connection timed out after {timeout_seconds}s attempting to connect to PostgreSQL at {safe_host}."
        logger.error(
            f"DATABASE\n"
            f"  URL: configured\n"
            f"  Driver: {safe_info['driver']}\n"
            f"  Connection: FAILED\n"
            f"  Reason: Timeout connecting to {safe_host}"
        )
        return False, msg
    except Exception as e:
        err_str = str(e)
        if "Connect call failed" in err_str or "ConnectionRefusedError" in err_str or "111" in err_str:
            msg = (
                f"Cannot establish connection to PostgreSQL at {safe_host}. "
                "In Railway: verify that your PostgreSQL service is running and DATABASE_URL variable is linked."
            )
        elif "password authentication failed" in err_str:
            msg = f"Password authentication failed for user '{safe_info['user']}' at {safe_host}."
        elif "database" in err_str and "does not exist" in err_str:
            msg = f"Database '{safe_info['database']}' does not exist on {safe_host}."
        else:
            msg = f"Database error connecting to {safe_host}: {err_str[:120]}"

        logger.error(
            f"DATABASE\n"
            f"  URL: configured\n"
            f"  Driver: {safe_info['driver']}\n"
            f"  Connection: FAILED\n"
            f"  Reason: {msg}"
        )
        return False, msg


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
