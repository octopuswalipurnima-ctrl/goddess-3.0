"""
Gemini AI Failover, Credential Rotation & Priority Queue Tests.

Verifies key rotation under quota/rate limits, model fallback to flash-lite,
and strict priority enforcement (HIGH moderation traffic must never be starved by NORMAL co-host traffic).
Zero secret exposure in exceptions, metrics, or logs.
"""

import asyncio
import pytest

from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import ModelUnavailableError
from app.services.gemini.models import AIRequest, AIRequestPriority
from app.services.gemini.queue import PriorityRequestQueue
from app.services.gemini.router import ModelRouter


@pytest.mark.asyncio
async def test_gemini_credential_rotation_on_quota_error():
    """Verify Gemini credential manager rotates to the next valid key on 429 quota error."""
    mgr = GeminiCredentialManager(keys=["AIzaSyKey11111111111111111111111", "AIzaSyKey22222222222222222222222"])
    
    key_id, raw_key = mgr.get_credential()
    assert raw_key == "AIzaSyKey11111111111111111111111"

    # Report quota failure on active key with cooldown
    await mgr.mark_failed(key_id, "Quota Exceeded", is_quota=True, cooldown_seconds=60)

    # Next credential fetch should return key 2
    key_id_2, raw_key_2 = mgr.get_credential()
    assert raw_key_2 == "AIzaSyKey22222222222222222222222"


def test_gemini_model_router_fallback():
    """Verify router selects fallback model gemini-2.5-flash-lite when primary model is degraded."""
    router = ModelRouter(primary_model="gemini-2.5-flash", fallback_model="gemini-2.5-flash-lite")
    req = AIRequest(stream_id="STREAM_A", task_type="moderation", prompt="Test")
    
    assert router.select_model(req, use_fallback=False) == "gemini-2.5-flash"
    assert router.select_model(req, use_fallback=True) == "gemini-2.5-flash-lite"
    assert router.should_fallback(ModelUnavailableError("Model overloaded")) is True


@pytest.mark.asyncio
async def test_gemini_priority_queue_moderation_precedence():
    """Verify HIGH priority (moderation) requests are popped before NORMAL priority (co-host) requests."""
    queue = PriorityRequestQueue(max_queue_size=100)

    # Enqueue NORMAL requests first
    req_normal_1 = AIRequest(stream_id="STREAM_A", task_type="cohost", prompt="Co-Host message 1", priority=AIRequestPriority.NORMAL)
    req_normal_2 = AIRequest(stream_id="STREAM_A", task_type="cohost", prompt="Co-Host message 2", priority=AIRequestPriority.NORMAL)
    await queue.enqueue(req_normal_1)
    await queue.enqueue(req_normal_2)

    # Enqueue HIGH priority request afterward
    req_high = AIRequest(stream_id="STREAM_A", task_type="moderation", prompt="URGENT Moderation evaluation", priority=AIRequestPriority.HIGH)
    await queue.enqueue(req_high)

    # Pop: The HIGH priority request must be popped first!
    item1 = await queue.get_next()
    assert item1.request.priority == AIRequestPriority.HIGH
    assert item1.request.prompt == "URGENT Moderation evaluation"

    item2 = await queue.get_next()
    assert item2.request.priority == AIRequestPriority.NORMAL
