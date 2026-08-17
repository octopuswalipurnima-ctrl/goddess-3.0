"""
Tests for Multi-Stream Isolation with Shared Provider Infrastructure.
"""

import pytest
from app.services.gemini.models import AIRequest, AIRequestPriority
from app.services.gemini.queue import PriorityRequestQueue


@pytest.mark.asyncio
async def test_multi_stream_request_tagging_and_isolation():
    """Verify requests from different streams retain isolated metadata and stream_ids."""
    queue = PriorityRequestQueue(max_queue_size=20)

    req_a = AIRequest(stream_id="STREAM_A", task_type="moderation", prompt="Prompt for Stream A", priority=AIRequestPriority.HIGH)
    req_b = AIRequest(stream_id="STREAM_B", task_type="cohost", prompt="Prompt for Stream B", priority=AIRequestPriority.NORMAL)
    req_c = AIRequest(stream_id="STREAM_C", task_type="summary", prompt="Prompt for Stream C", priority=AIRequestPriority.LOW)

    await queue.enqueue(req_a)
    await queue.enqueue(req_b)
    await queue.enqueue(req_c)

    item1 = await queue.get_next()
    assert item1.request.stream_id == "STREAM_A"
    assert item1.request.priority == AIRequestPriority.HIGH

    item2 = await queue.get_next()
    assert item2.request.stream_id == "STREAM_B"

    item3 = await queue.get_next()
    assert item3.request.stream_id == "STREAM_C"
