"""
Tests for Asynchronous Internal Event Bus.
"""

import pytest
from app.core.events import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Verify event bus pub/sub execution."""
    bus = EventBus()
    received_payloads = []

    async def sample_handler(payload: dict):
        received_payloads.append(payload)

    bus.subscribe("STREAM_STARTED", sample_handler)

    test_payload = {"stream_id": "stream_123", "title": "Live Stream"}
    await bus.publish("STREAM_STARTED", test_payload)

    assert len(received_payloads) == 1
    assert received_payloads[0]["stream_id"] == "stream_123"

    # Unsubscribe test
    bus.unsubscribe("STREAM_STARTED", sample_handler)
    await bus.publish("STREAM_STARTED", {"stream_id": "stream_456"})
    assert len(received_payloads) == 1  # No new items received


@pytest.mark.asyncio
async def test_event_bus_error_isolation():
    """Verify that a failing subscriber does not prevent other subscribers from receiving the event."""
    bus = EventBus()
    received_by_healthy = []

    async def failing_handler(payload: dict):
        raise ValueError("Intentional simulated error in subscriber")

    async def healthy_handler(payload: dict):
        received_by_healthy.append(payload)

    bus.subscribe("CHAT_MESSAGE", failing_handler)
    bus.subscribe("CHAT_MESSAGE", healthy_handler)

    await bus.publish("CHAT_MESSAGE", {"message": "Hello world"})

    assert len(received_by_healthy) == 1
    assert received_by_healthy[0]["message"] == "Hello world"
