"""
Tests for Priority-Based Gemini Request Queue and Concurrency Limits.
"""

import pytest
from app.services.gemini.exceptions import QueueFullError
from app.services.gemini.models import AIRequest, AIRequestPriority
from app.services.gemini.queue import PriorityRequestQueue


@pytest.mark.asyncio
async def test_priority_queue_ordering():
    """Verify that HIGH priority items are dequeued before NORMAL or LOW items."""
    queue = PriorityRequestQueue(max_concurrency=2, max_queue_size=10)

    req_low = AIRequest(stream_id="s1", prompt="Low task", priority=AIRequestPriority.LOW)
    req_normal = AIRequest(stream_id="s1", prompt="Normal task", priority=AIRequestPriority.NORMAL)
    req_high = AIRequest(stream_id="s1", prompt="High moderation task", priority=AIRequestPriority.HIGH)

    # Enqueue in reverse priority order: LOW, NORMAL, HIGH
    await queue.enqueue(req_low)
    await queue.enqueue(req_normal)
    await queue.enqueue(req_high)

    assert queue.queued_count == 3

    # First dequeued MUST be HIGH
    first_item = await queue.get_next()
    assert first_item.request.priority == AIRequestPriority.HIGH
    assert first_item.request.prompt == "High moderation task"

    # Second dequeued MUST be NORMAL
    second_item = await queue.get_next()
    assert second_item.request.priority == AIRequestPriority.NORMAL

    # Third dequeued MUST be LOW
    third_item = await queue.get_next()
    assert third_item.request.priority == AIRequestPriority.LOW


@pytest.mark.asyncio
async def test_queue_bounded_capacity():
    """Verify that exceeding max_queue_size raises QueueFullError."""
    queue = PriorityRequestQueue(max_concurrency=2, max_queue_size=2)

    req1 = AIRequest(stream_id="s1", prompt="Prompt 1")
    req2 = AIRequest(stream_id="s1", prompt="Prompt 2")
    req3 = AIRequest(stream_id="s1", prompt="Prompt 3")

    await queue.enqueue(req1)
    await queue.enqueue(req2)

    with pytest.raises(QueueFullError):
        await queue.enqueue(req3)
