"""Alembic environment configuration with diagnostic logging and safe database URL resolution."""

import asyncio
import logging
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401
from alembic import context
from app.database import Base, get_db_url
from app.utils import mask_database_url

logger = logging.getLogger("alembic.env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_db_url()
    safe_info = mask_database_url(url)
    logger.info(f"Running offline migrations against: {safe_info['safe_summary']}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine and associate a connection with the context."""
    db_url = get_db_url()
    safe_info = mask_database_url(db_url)
    logger.info(f"Connecting to database for schema migrations: {safe_info['safe_summary']}")

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        logger.info("Executing database migration steps...")
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
    logger.info("Database migrations completed successfully.")
    sys.stdout.flush()
    sys.stderr.flush()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
