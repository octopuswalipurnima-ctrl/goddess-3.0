"""
Tests for database connection failures and graceful health degradation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.db.session import ping_database


@pytest.mark.asyncio
async def test_database_connection_failure_health_degradation():
    """Verify ping_database reports UNAVAILABLE when database connection fails."""
    mock_conn = AsyncMock()
    mock_conn.__aenter__.side_effect = ConnectionRefusedError("Connection refused by database server")

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    with patch("app.db.session.get_engine", return_value=mock_engine):
        res = await ping_database()
        assert res["status"] == "UNAVAILABLE"
        assert "ConnectionRefusedError" in res["details"]
        assert res["latency_ms"] is None
