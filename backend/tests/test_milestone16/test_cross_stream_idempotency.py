"""
Tests for Cross-Stream Idempotency Isolation in GODDESS AI 2.0.
"""

import pytest
from app.core.idempotency import ActionIdempotencyManager


@pytest.mark.asyncio
async def test_cross_stream_idempotency_isolation():
    """Verify action ID on STREAM_A does not block identical action ID on STREAM_B."""
    mgr = ActionIdempotencyManager()

    # Action 1 on STREAM_A
    res_a = await mgr.register_action("action_msg_100", stream_id="STREAM_A")
    assert res_a is True

    # Same Action 1 on STREAM_B should be allowed
    res_b = await mgr.register_action("action_msg_100", stream_id="STREAM_B")
    assert res_b is True

    # Repeating on STREAM_A should be blocked
    res_a_repeat = await mgr.register_action("action_msg_100", stream_id="STREAM_A")
    assert res_a_repeat is False
