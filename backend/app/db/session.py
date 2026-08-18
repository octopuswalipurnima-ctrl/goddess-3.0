"""
Asynchronous Database Engine and Session Management for GODDESS AI 2.0.

Provides SQLAlchemy 2.x async engine configuration, connection pooling,
transaction-safe session context managers, and health check diagnostics.
"""

from contextlib import asynccontextmanager
import time
from typing import AsyncGenerator, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("db.session")

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(url: Optional[str]) -> Optional[str]:
    """Ensure database URL specifies appropriate async dialect (asyncpg / aiosqlite)."""
    if not url or not url.strip():
        return None
    url = url.strip()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def get_engine(database_url: Optional[str] = None) -> Optional[AsyncEngine]:
    """Get or create singleton AsyncEngine with connection pooling and timeouts."""
    global _engine
    url = normalize_database_url(database_url or settings.database_url)
    if not url:
        return None

    if _engine is None:
        is_sqlite = "sqlite" in url
        engine_kwargs: Dict[str, Any] = {
            "echo": settings.db_echo,
            "future": True,
        }

        if is_sqlite:
            # SQLite uses NullPool or StaticPool for in-memory / file tests
            engine_kwargs["poolclass"] = NullPool
        else:
            # PostgreSQL uses AsyncAdaptedQueuePool with configured pool sizing
            engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
            engine_kwargs["pool_size"] = settings.db_pool_size
            engine_kwargs["max_overflow"] = settings.db_max_overflow
            engine_kwargs["pool_timeout"] = settings.db_pool_timeout
            engine_kwargs["pool_recycle"] = settings.db_pool_recycle
            engine_kwargs["pool_pre_ping"] = True

        _engine = create_async_engine(url, **engine_kwargs)
        logger.info(f"Initialized async database engine (dialect: {'sqlite' if is_sqlite else 'postgresql'}).")

    return _engine


def get_sessionmaker(engine: Optional[AsyncEngine] = None) -> Optional[async_sessionmaker[AsyncSession]]:
    """Get or create singleton async_sessionmaker bound to the AsyncEngine."""
    global _sessionmaker
    active_engine = engine or get_engine()
    if not active_engine:
        return None

    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=active_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _sessionmaker


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Transaction-safe async context manager for database sessions.
    Automatically commits on successful block exit, or rolls back on exception.
    """
    sm = get_sessionmaker()
    if not sm:
        raise RuntimeError("Database is not configured or engine failed to initialize.")

    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception as err:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {err}")
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining a scoped async database session."""
    async with get_db_session() as session:
        yield session


async def ping_database() -> Dict[str, Any]:
    """
    Diagnostic health probe checking database connectivity, latency, and connection pool metrics.
    Never exposes credentials.
    """
    engine = get_engine()
    if not engine:
        return {
            "status": "NOT_CONFIGURED",
            "details": "DATABASE_URL is not configured",
            "latency_ms": None,
            "pool": None,
        }

    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Extract pool stats if QueuePool
        pool_stats = None
        pool = getattr(engine, "pool", None)
        if pool and hasattr(pool, "size"):
            pool_stats = {
                "size": pool.size(),
                "checkedin": pool.checkedin(),
                "checkedout": pool.checkedout(),
                "overflow": pool.overflow(),
            }

        return {
            "status": "HEALTHY",
            "details": "Database connection verified",
            "latency_ms": latency_ms,
            "pool": pool_stats,
        }
    except Exception as exc:
        logger.warning(f"Database health ping failed: {exc}")
        return {
            "status": "UNAVAILABLE",
            "details": f"Database connection error: {type(exc).__name__}",
            "latency_ms": None,
            "pool": None,
        }


async def close_db() -> None:
    """Gracefully dispose database engine and cleanup connection pools."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("Database engine disposed.")
