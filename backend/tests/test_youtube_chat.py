"""
Tests for LiveChatReader, Message Deduplication, and Event Dispatches.
"""

import asyncio
import pytest
from app.core.events import event_bus
from app.services.youtube.chat import LiveChatReader
from app.services.youtube.models import ChatMessage


class MockYouTubeClient:
    """Mock client returning controllable chat messages."""

    def __init__(self, message_batches=None):
        self.batches = message_batches or []
        self.call_count = 0

    async def get_live_chat_messages(self, live_chat_id: str, page_token: str = None):
        if self.call_count < len(self.batches):
            batch = self.batches[self.call_count]
            self.call_count += 1
            return batch, f"token_{self.call_count}", 100
        return [], None, 100


@pytest.mark.asyncio
async def test_live_chat_deduplication_and_event_publishing():
    """Verify that messages are published to Event Bus and duplicate IDs are discarded."""
    msg1 = ChatMessage(
        message_id="msg_1001",
        stream_id="chat_test",
        channel_id="ch_1",
        author_id="user_1",
        author_name="UserOne",
        message_text="First message",
        published_at="2026-08-16T12:00:00Z",
    )
    msg2 = ChatMessage(
        message_id="msg_1002",
        stream_id="chat_test",
        channel_id="ch_2",
        author_id="user_2",
        author_name="UserTwo",
        message_text="Second message",
        published_at="2026-08-16T12:00:05Z",
    )

    # Batch 1: returns [msg1, msg2]
    # Batch 2: returns [msg1, msg2] (Overlapping repeat from reconnect)
    mock_client = MockYouTubeClient(message_batches=[[msg1, msg2], [msg1, msg2]])
    reader = LiveChatReader(stream_id="stream_abc", live_chat_id="chat_test", api_client=mock_client)

    received_chat_events = []

    async def on_chat_message(payload: dict):
        received_chat_events.append(payload)

    event_bus.subscribe("CHAT_MESSAGE", on_chat_message)

    # Start reader for 350ms to consume both batches
    await reader.start()
    await asyncio.sleep(0.35)
    await reader.stop()

    event_bus.unsubscribe("CHAT_MESSAGE", on_chat_message)

    # Exactly 2 messages should have been dispatched, despite the overlapping duplicate batch
    assert len(received_chat_events) == 2
    assert received_chat_events[0]["message"]["message_id"] == "msg_1001"
    assert received_chat_events[1]["message"]["message_id"] == "msg_1002"
    assert reader.metrics.messages_received == 2
