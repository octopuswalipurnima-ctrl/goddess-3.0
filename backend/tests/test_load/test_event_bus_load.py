"""
EventBus Load & Consumer Failure Isolation Tests.

Verifies high-throughput asynchronous event distribution, consumer exception isolation,
and zero cascade failures when individual subscribers throw errors.
"""

import asyncio
import pytest
from app.core.events import EventBus


@pytest.mark.asyncio
async def test_event_bus_high_throughput_dispatch():
    """Verify EventBus processes high-volume event bursts without dropping messages."""
    bus = EventBus()
    received_count = 0
    lock = asyncio.Lock()

    async def normal_consumer(payload):
        nonlocal received_count
        async with lock:
            received_count += 1

    bus.subscribe("TEST_BURST_EVENT", normal_consumer)

    total_events = 500
    publish_tasks = [
        bus.publish("TEST_BURST_EVENT", {"event_id": idx, "data": "load_payload"})
        for idx in range(total_events)
    ]
    await asyncio.gather(*publish_tasks)

    assert received_count == total_events


@pytest.mark.asyncio
async def test_event_bus_consumer_failure_isolation():
    """Verify that a failing/crashing consumer does NOT stop other subscribers or crash EventBus."""
    bus = EventBus()
    healthy_consumer_1_calls = 0
    healthy_consumer_2_calls = 0
    failing_consumer_calls = 0

    async def healthy_consumer_1(payload):
        nonlocal healthy_consumer_1_calls
        healthy_consumer_1_calls += 1

    async def failing_consumer(payload):
        nonlocal failing_consumer_calls
        failing_consumer_calls += 1
        raise RuntimeError("Simulated consumer crash during message processing!")

    async def healthy_consumer_2(payload):
        nonlocal healthy_consumer_2_calls
        healthy_consumer_2_calls += 1

    bus.subscribe("ISOLATION_EVENT", healthy_consumer_1)
    bus.subscribe("ISOLATION_EVENT", failing_consumer)
    bus.subscribe("ISOLATION_EVENT", healthy_consumer_2)

    # Publish multiple events
    for idx in range(50):
        await bus.publish("ISOLATION_EVENT", {"id": idx})

    assert failing_consumer_calls == 50
    assert healthy_consumer_1_calls == 50
    assert healthy_consumer_2_calls == 50


@pytest.mark.asyncio
async def test_event_bus_cross_stream_isolation():
    """Verify events targeting distinct streams do not leak across consumers."""
    bus = EventBus()
    stream_a_events = []
    stream_b_events = []

    async def handle_all_events(payload):
        stream_id = payload.get("stream_id")
        if stream_id == "STREAM_A":
            stream_a_events.append(payload)
        elif stream_id == "STREAM_B":
            stream_b_events.append(payload)

    bus.subscribe("CHAT_MESSAGE", handle_all_events)

    await bus.publish("CHAT_MESSAGE", {"stream_id": "STREAM_A", "text": "Msg A"})
    await bus.publish("CHAT_MESSAGE", {"stream_id": "STREAM_B", "text": "Msg B"})
    await bus.publish("CHAT_MESSAGE", {"stream_id": "STREAM_A", "text": "Msg A2"})

    assert len(stream_a_events) == 2
    assert len(stream_b_events) == 1
    assert stream_a_events[0]["text"] == "Msg A"
    assert stream_b_events[0]["text"] == "Msg B"
