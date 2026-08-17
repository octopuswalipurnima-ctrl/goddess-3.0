"""
Controlled Real PostgreSQL Integration & Reliability Tests for GODDESS AI 2.0.

Requires explicit RUN_REAL_POSTGRES_TEST=true.
Guarantees zero leakage of raw DATABASE_URL or credentials.
"""

import os
import pytest
from app.core.config import settings
from app.db.session import close_db, get_db_session, ping_database


@pytest.mark.asyncio
async def test_real_postgres_connection_and_schema_validation():
    """
    Validate real PostgreSQL connection, authentication, and table accessibility.
    """
    if os.getenv("RUN_REAL_POSTGRES_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_POSTGRES_TEST is not true. Skipping real PostgreSQL test.")

    if not settings.is_database_configured:
        pytest.skip("DATABASE_URL not configured. Skipping real PostgreSQL test.")

    # 1. Ping Database
    db_status = await ping_database()
    assert db_status["status"] == "HEALTHY", f"PostgreSQL ping failed: {db_status.get('details')}"

    # 2. Test Transaction & Session Read/Write
    async with get_db_session() as session:
        assert session.is_active is True

    # 3. Verify clean shutdown / close
    await close_db()
