"""
Real Service Integration Audit: PostgreSQL & SQLAlchemy 2.x Async Engine for GODDESS AI 2.0.
"""

import pytest
from app.db.session import get_engine, normalize_database_url, ping_database


def test_postgres_dialect_normalization():
    """Verify postgresql:// URLs are normalized to asyncpg dialect postgresql+asyncpg://."""
    url = "postgresql://user:pass@localhost:5432/goddess_db"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+asyncpg://")


@pytest.mark.asyncio
async def test_database_health_ping_safe_structure():
    """Verify ping_database returns structured status with zero password exposure."""
    res = await ping_database()
    assert "status" in res
    assert "details" in res
    assert res["status"] in ("HEALTHY", "NOT_CONFIGURED", "UNAVAILABLE")

    # Password must not appear in details
    assert "pass" not in res["details"].lower()
