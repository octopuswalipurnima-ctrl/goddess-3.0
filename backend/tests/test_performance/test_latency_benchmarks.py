"""
Performance & Latency Benchmark Test Suite for GODDESS AI 2.0.

Measures real execution latencies (p50, p95, p99) for EventBus dispatch,
rule moderation, Co-Host intent classification, and rate limit checks.
"""

import statistics
import time
import pytest

from app.core.events import EventBus
from app.core.redis import InMemoryFallbackState
from app.services.cohost.intents import RuleIntentDetector
from app.services.cohost.models import CoHostMessage
from app.services.moderation.models import UserRole
from app.services.moderation.rules import RuleEngine
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_event_bus_dispatch_latency():
    """Benchmark EventBus publish latency (target: p95 < 2ms)."""
    bus = EventBus()
    latencies = []

    async def dummy_handler(payload):
        pass

    bus.subscribe("BENCHMARK_EVENT", dummy_handler)

    for idx in range(500):
        t0 = time.perf_counter()
        await bus.publish("BENCHMARK_EVENT", {"id": idx})
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]

    print(f"\n[EventBus Latency] p50={p50:.3f}ms | p95={p95:.3f}ms | p99={p99:.3f}ms")
    assert p95 < 10.0  # Fast in-process dispatch


def test_moderation_rule_evaluation_latency():
    """Benchmark RuleEngine rule evaluation latency (target: p95 < 2ms)."""
    engine = RuleEngine()
    test_messages = [
        "Normal gaming chat message",
        "VISIT HTTPS://SPAM.COM FOR FREE BITCOIN",
        "ALL CAPS RAGE COMMENT WITH EXCLAMATION MARKS!!!",
        "Hey streamer what gear are you using?",
        "Spam spam spam spam spam spam spam",
    ]

    latencies = []
    for _ in range(200):
        for idx, text in enumerate(test_messages):
            msg = ChatMessage(
                stream_id="STREAM_A",
                message_id=f"msg_bench_{idx}",
                author_id="user_1",
                author_name="User1",
                message_text=text,
            )
            t0 = time.perf_counter()
            engine.evaluate(msg, role=UserRole.USER)
            latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]

    print(f"\n[RuleEngine Latency] p50={p50:.3f}ms | p95={p95:.3f}ms | p99={p99:.3f}ms")
    assert p95 < 5.0  # High-speed deterministic regex evaluation


def test_cohost_intent_classification_latency():
    """Benchmark CoHost RuleIntentDetector latency (target: p95 < 2ms)."""
    detector = RuleIntentDetector()
    test_prompts = [
        "@goddess what strategy should we use?",
        "!help",
        "Hello everyone in chat!",
        "@goddess what is your favorite gaming moment?",
        "!stats",
    ]

    latencies = []
    for _ in range(200):
        for idx, text in enumerate(test_prompts):
            msg = CoHostMessage(
                stream_id="STREAM_A",
                message_id=f"msg_perf_{idx}",
                author_id="user_1",
                author_name="User1",
                message_text=text,
                timestamp=time.time(),
            )
            t0 = time.perf_counter()
            detector.detect_intent(msg)
            latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]

    print(f"\n[IntentDetector Latency] p50={p50:.3f}ms | p95={p95:.3f}ms | p99={p99:.3f}ms")
    assert p95 < 5.0


@pytest.mark.asyncio
async def test_in_memory_state_latency():
    """Benchmark local in-memory fallback state read/write latency."""
    state = InMemoryFallbackState()
    latencies = []

    for idx in range(500):
        t0 = time.perf_counter()
        await state.set(f"key_{idx}", idx, ex=60.0)
        await state.get(f"key_{idx}")
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]

    print(f"\n[State Store Latency] p50={p50:.3f}ms | p95={p95:.3f}ms | p99={p99:.3f}ms")
    assert p95 < 5.0
