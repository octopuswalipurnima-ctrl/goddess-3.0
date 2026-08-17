"""
Tests for GeminiAIManager, End-to-End Execution, Empty-Response Handling, and Multi-Stream Isolation.
"""

import asyncio
import pytest
from app.services.gemini.credentials import GeminiCredentialManager
from app.services.gemini.exceptions import (
    EmptyResponseError,
    GeminiAPIError,
    RateLimitError,
)
from app.services.gemini.manager import GeminiAIManager
from app.services.gemini.models import (
    AIRequest,
    AIRequestPriority,
    AIResponseStatus,
)
from app.services.gemini.queue import PriorityRequestQueue
from app.services.gemini.rate_limiter import TokenBucketRateLimiter
from app.services.gemini.router import ModelRouter


class MockGeminiClient:
    """Configurable mock client simulating successes, fallbacks, rate limits, and empty outputs."""

    def __init__(self, behavior_map=None):
        self.behavior_map = behavior_map or {}
        self.call_history = []

    async def generate_content(
        self,
        prompt: str,
        model: str,
        raw_key: str,
        system_instruction: str = None,
        temperature: float = None,
        max_output_tokens: int = None,
        timeout: float = None,
    ):
        self.call_history.append({"prompt": prompt, "model": model, "key": raw_key})

        if prompt in self.behavior_map:
            behavior = self.behavior_map[prompt]
            if isinstance(behavior, Exception):
                raise behavior
            if callable(behavior):
                return behavior(model, raw_key)
            return behavior, "STOP", {"total_tokens": 20}

        return f"Response for: {prompt} (Model: {model})", "STOP", {"total_tokens": 25}


@pytest.mark.asyncio
async def test_manager_successful_request():
    """Verify full end-to-end generation request."""
    mock_client = MockGeminiClient()
    creds = GeminiCredentialManager(keys=["KeyOne"])
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
    queue = PriorityRequestQueue(max_concurrency=2)
    router = ModelRouter()

    manager = GeminiAIManager(
        credentials=creds,
        client=mock_client,
        router=router,
        rate_limiter=limiter,
        queue=queue,
    )

    req = AIRequest(stream_id="stream_1", prompt="What is live streaming?", priority=AIRequestPriority.HIGH)
    resp = await manager.request(req)

    assert resp.status == AIResponseStatus.SUCCESS
    assert "What is live streaming?" in resp.text
    assert resp.model == "gemini-2.5-flash"
    assert resp.credential_id == "gemini-key-1"
    assert resp.stream_id == "stream_1"

    await manager.shutdown()


@pytest.mark.asyncio
async def test_manager_model_fallback_on_503():
    """Verify that 503 error on primary model falls back to fallback model."""
    call_count = 0

    def behavior(model, raw_key):
        nonlocal call_count
        call_count += 1
        if model == "gemini-2.5-flash":
            raise GeminiAPIError(503, "Primary model overloaded")
        return "Fallback content generated!", "STOP", {"total_tokens": 10}

    mock_client = MockGeminiClient(behavior_map={"Test fallback": behavior})
    creds = GeminiCredentialManager(keys=["KeyOne"])
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
    queue = PriorityRequestQueue(max_concurrency=2)
    router = ModelRouter(primary_model="gemini-2.5-flash", fallback_model="gemini-2.5-flash-lite")

    manager = GeminiAIManager(
        credentials=creds,
        client=mock_client,
        router=router,
        rate_limiter=limiter,
        queue=queue,
    )

    req = AIRequest(stream_id="stream_1", prompt="Test fallback")
    resp = await manager.request(req)

    assert resp.status == AIResponseStatus.SUCCESS
    assert resp.text == "Fallback content generated!"
    assert resp.model == "gemini-2.5-flash-lite"
    assert manager.metrics.model_fallbacks_count >= 1

    await manager.shutdown()


@pytest.mark.asyncio
async def test_manager_empty_response_classification():
    """Verify that empty response from Gemini is honestly classified as EMPTY_RESPONSE."""
    mock_client = MockGeminiClient(
        behavior_map={"Trigger empty": EmptyResponseError("Empty candidate parts")}
    )
    creds = GeminiCredentialManager(keys=["KeyOne"])
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
    queue = PriorityRequestQueue(max_concurrency=2)
    router = ModelRouter()

    manager = GeminiAIManager(
        credentials=creds,
        client=mock_client,
        router=router,
        rate_limiter=limiter,
        queue=queue,
        max_retries=1,
    )

    req = AIRequest(stream_id="stream_1", prompt="Trigger empty")
    resp = await manager.request(req)

    assert resp.status == AIResponseStatus.EMPTY_RESPONSE
    assert resp.text == ""
    assert "Empty candidate parts" in resp.error_message
    assert manager.metrics.empty_responses >= 1

    await manager.shutdown()


@pytest.mark.asyncio
async def test_multi_stream_isolation_and_no_contamination():
    """
    CRITICAL: Verify that concurrent AI requests for Stream A and Stream B
    remain completely isolated without cross-stream contamination.
    """
    mock_client = MockGeminiClient()
    creds = GeminiCredentialManager(keys=["KeyOne"])
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
    queue = PriorityRequestQueue(max_concurrency=4)
    router = ModelRouter()

    manager = GeminiAIManager(
        credentials=creds,
        client=mock_client,
        router=router,
        rate_limiter=limiter,
        queue=queue,
    )

    # Launch 4 concurrent requests across 4 distinct streams
    req_a = AIRequest(stream_id="stream_A", prompt="Prompt for Stream A")
    req_b = AIRequest(stream_id="stream_B", prompt="Prompt for Stream B")
    req_c = AIRequest(stream_id="stream_C", prompt="Prompt for Stream C")
    req_d = AIRequest(stream_id="stream_D", prompt="Prompt for Stream D")

    results = await asyncio.gather(
        manager.request(req_a),
        manager.request(req_b),
        manager.request(req_c),
        manager.request(req_d),
    )

    resp_a, resp_b, resp_c, resp_d = results

    # Verify each response strictly matches its originating stream ID and prompt
    assert resp_a.stream_id == "stream_A"
    assert "Prompt for Stream A" in resp_a.text

    assert resp_b.stream_id == "stream_B"
    assert "Prompt for Stream B" in resp_b.text

    assert resp_c.stream_id == "stream_C"
    assert "Prompt for Stream C" in resp_c.text

    assert resp_d.stream_id == "stream_D"
    assert "Prompt for Stream D" in resp_d.text

    await manager.shutdown()
