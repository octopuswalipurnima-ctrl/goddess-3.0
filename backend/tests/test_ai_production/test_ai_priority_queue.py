"""
Tests for Gemini Priority Request Queue in GODDESS AI 2.0.
"""

import pytest
from app.services.gemini.models import AIRequest, AIRequestPriority
from app.services.gemini.queue import PriorityRequestQueue


@pytest.mark.asyncio
async def test_priority_queue_moderation_before_cohost():
    """Verify HIGH priority moderation requests jump ahead of NORMAL Co-Host requests."""
    queue = PriorityRequestQueue(max_queue_size=100)

    req_cohost_1 = AIRequest(stream_id="STREAM_1", prompt="CoHost 1", priority=AIRequestPriority.NORMAL)
    req_cohost_2 = AIRequest(stream_id="STREAM_1", prompt="CoHost 2", priority=AIRequestPriority.NORMAL)
    req_mod = AIRequest(stream_id="STREAM_1", prompt="Mod Emergency", priority=AIRequestPriority.HIGH)

    # Enqueue normal items first
    fut1 = await queue.enqueue(req_cohost_1)
    fut2 = await queue.enqueue(req_cohost_2)
    fut3 = await queue.enqueue(req_mod)

    # Dequeue first item: must be the HIGH priority moderation request
    item1 = await queue.get_next()
    assert item1.request.priority == AIRequestPriority.HIGH
    assert item1.request.prompt == "Mod Emergency"

    # Dequeue remaining items
    item2 = await queue.get_next()
    assert item2.request.priority == AIRequestPriority.NORMAL
