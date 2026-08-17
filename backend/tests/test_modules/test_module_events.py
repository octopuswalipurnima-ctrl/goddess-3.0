"""
Tests for Module EventBus routing and subscription filtering.
"""

import pytest

from app.modules.base import BaseModule
from app.modules.manager import ModuleManager
from app.modules.models import ModuleMetadata
from app.modules.registry import ModuleRegistry


class EventTestModule(BaseModule):
    def __init__(self, mod_id: str, events: list[str]):
        super().__init__(ModuleMetadata(id=mod_id, name=f"Module {mod_id}", supported_events=events))
        self.events_seen = []

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        self.events_seen.append(event_name)


@pytest.mark.asyncio
async def test_module_receives_only_supported_events():
    registry = ModuleRegistry()
    chat_mod = EventTestModule("chat_listener", ["CHAT_MESSAGE"])
    stream_mod = EventTestModule("stream_listener", ["STREAM_STARTED"])

    registry.register(chat_mod)
    registry.register(stream_mod)

    manager = ModuleManager(registry=registry)
    await manager.start_all()

    # Dispatch CHAT_MESSAGE
    await manager._dispatch_event("CHAT_MESSAGE", {"stream_id": "stream_1"})

    assert chat_mod.events_seen == ["CHAT_MESSAGE"]
    assert stream_mod.events_seen == []

    # Dispatch STREAM_STARTED
    await manager._dispatch_event("STREAM_STARTED", {"stream_id": "stream_1"})

    assert chat_mod.events_seen == ["CHAT_MESSAGE"]
    assert stream_mod.events_seen == ["STREAM_STARTED"]
