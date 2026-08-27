"""Production startup runner for Goddess AI 3.0."""

import os
import sys

import uvicorn
from alembic.config import Config

from alembic import command
from app.utils import get_logger, setup_logging

logger = get_logger("goddess.startup")


def run_migrations() -> None:
    """Run Alembic migrations before starting web server."""
    logger.info("STARTUP: database migrations beginning")
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("STARTUP: database migrations completed")
    except Exception as e:
        logger.error(f"STARTUP: database migration failed: {e}", exc_info=True)
        env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "production").lower()
        if env in ("production", "prod"):
            sys.exit(1)


def main() -> None:
    """Run migrations and start Uvicorn ASGI server."""
    setup_logging()
    logger.info("STARTUP: process beginning")
    run_migrations()

    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0"
    logger.info(f"STARTUP: binding to {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=1,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
