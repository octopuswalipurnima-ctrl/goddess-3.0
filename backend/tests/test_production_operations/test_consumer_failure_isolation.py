"""
Tests for EventBus Consumer Exception Isolation in GODDESS AI 2.0.
"""

import pytest
from app.core.events import EventBus


@pytest.mark.asyncio
async def test_event_bus_failing_handler_does_not_break_other_handlers():
    """Verify an exception inside one subscriber handler does not prevent other subscribers from receiving the event."""
    bus = EventBus()

    received_by_healthy = []

    async def failing_handler(data):
        raise RuntimeError("Simulated unhandled consumer error")

    async def healthy_handler(data):
        received_by_healthy.append(data)

    bus.subscribe("TEST_EVENT", failing_handler)
    bus.subscribe("TEST_EVENT", healthy_handler)

    # Publish event
    await bus.publish("TEST_EVENT", {"payload": "safe_data"})

    assert len(received_by_healthy) == 1
    assert received_by_healthy[0]["payload"] == "safe_data"
