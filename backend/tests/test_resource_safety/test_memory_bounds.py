"""
Resource Safety & Bounded Memory Test Suite for GODDESS AI 2.0.

Verifies that no queue, buffer, context window, or in-memory state store
can grow unboundedly under sustained high traffic.
"""

import time
import pytest
from app.core.redis import InMemoryFallbackState, MAX_FALLBACK_KEYS
from app.services.cohost.context import StreamContext
from app.services.cohost.models import CoHostMessage
from app.services.gemini.models import AIRequest, AIRequestPriority
from app.services.gemini.queue import PriorityRequestQueue
from app.services.moderation.audit import ModerationAuditLogger
from app.services.moderation.models import ActionStatus, ModerationAction, ModerationDecision


def test_cohost_context_window_bounded_to_20_messages():
    """Verify stream context memory strictly maintains a sliding window of max 20 messages."""
    ctx = StreamContext(stream_id="STREAM_TEST", max_stream_messages=20, max_user_messages=5)
    
    # Add 100 messages
    for idx in range(100):
        msg = CoHostMessage(
            stream_id="STREAM_TEST",
            message_id=f"msg_{idx}",
            author_id=f"user_{idx % 10}",
            author_name=f"User_{idx % 10}",
            message_text=f"Message {idx}",
            timestamp=time.time(),
        )
        ctx.add_viewer_message(msg)

    assert len(ctx.stream_history) == 20
    role, name, text, _ = ctx.stream_history[-1]
    assert text == "Message 99"


def test_cohost_per_user_context_bounded_to_5_messages():
    """Verify per-user context memory strictly maintains a sliding window of max 5 messages."""
    ctx = StreamContext(stream_id="STREAM_TEST", max_stream_messages=20, max_user_messages=5)

    for idx in range(20):
        msg = CoHostMessage(
            stream_id="STREAM_TEST",
            message_id=f"msg_{idx}",
            author_id="user_target",
            author_name="TargetUser",
            message_text=f"User msg {idx}",
            timestamp=time.time(),
        )
        ctx.add_viewer_message(msg)

    user_history = ctx.user_history["user_target"]
    assert len(user_history) == 5
    last_text, _ = user_history[-1]
    assert last_text == "User msg 19"


@pytest.mark.asyncio
async def test_moderation_audit_buffer_bounded():
    """Verify ModerationAuditLogger in-memory buffer caps at max_records_per_stream (1000)."""
    audit = ModerationAuditLogger(max_records_per_stream=1000)

    for idx in range(1500):
        decision = ModerationDecision(
            stream_id="STREAM_AUDIT",
            message_id=f"msg_{idx}",
            author_id="user_spammer",
            author_name="Spammer",
            message_text=f"Spam text {idx}",
            recommended_action=ModerationAction.BLOCK,
            reason="Spam rule",
        )
        await audit.record_audit(
            decision=decision,
            action_taken=ModerationAction.BLOCK,
            action_status=ActionStatus.APPROVED,
        )

    records = audit.get_recent_records("STREAM_AUDIT", limit=2000)
    assert len(records) <= 1000


@pytest.mark.asyncio
async def test_gemini_request_queue_bounded_size():
    """Verify PriorityRequestQueue rejects requests when queue is at maximum capacity (10)."""
    from app.services.gemini.exceptions import QueueFullError
    queue = PriorityRequestQueue(max_queue_size=10)

    for idx in range(10):
        req = AIRequest(stream_id="STREAM_A", task_type="test", prompt=f"Prompt {idx}", priority=AIRequestPriority.NORMAL)
        fut = await queue.enqueue(req)
        assert fut is not None

    # 11th request must raise QueueFullError
    overflow_req = AIRequest(stream_id="STREAM_A", task_type="test", prompt="Overflow Prompt", priority=AIRequestPriority.NORMAL)
    with pytest.raises(QueueFullError):
        await queue.enqueue(overflow_req)

    assert queue.queued_count == 10
