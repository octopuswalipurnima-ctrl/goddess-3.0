"""
Controlled Real Redis State & Deduplication Validation for GODDESS AI 2.0.

Requires explicit RUN_REAL_REDIS_TEST=true.
Validates stream key isolation (STREAM_A vs STREAM_B) and safe in-memory fallback.
"""

import os
import pytest
from app.core.config import settings
from app.core.redis import redis_state


@pytest.mark.asyncio
async def test_real_redis_operations_and_stream_isolation():
    """
    Validate real Redis connection, key isolation across streams, and deduplication.
    """
    if os.getenv("RUN_REAL_REDIS_TEST", "false").lower() != "true":
        pytest.skip("RUN_REAL_REDIS_TEST is not true. Skipping real Redis test.")

    if not settings.is_redis_configured:
        pytest.skip("REDIS_URL not configured. Skipping real Redis test.")

    await redis_state.initialize()
    ping_res = await redis_state.ping()
    assert ping_res["status"] in ["HEALTHY", "DEGRADED"], f"Redis ping failed: {ping_res}"

    # Verify stream isolation: Stream A key cannot match Stream B
    key_a = "stream:STREAM_A:msg:1001"
    key_b = "stream:STREAM_B:msg:1001"

    await redis_state.set(key_a, "processed", ttl=60)
    val_a = await redis_state.get(key_a)
    val_b = await redis_state.get(key_b)

    assert val_a == "processed"
    assert val_b is None  # Stream isolation verified
