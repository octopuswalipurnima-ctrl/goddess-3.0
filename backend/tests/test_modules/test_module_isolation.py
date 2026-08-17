"""
Tests for Module failure isolation.
"""

import pytest

from app.modules.base import BaseModule
from app.modules.manager import ModuleManager
from app.modules.models import ModuleMetadata, ModuleStatus
from app.modules.registry import ModuleRegistry


class CrashingModule(BaseModule):
    def __init__(self):
        super().__init__(
            ModuleMetadata(
                id="crash_mod",
                name="Crashing Module",
                supported_events=["CHAT_MESSAGE"],
            )
        )

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        raise RuntimeError("Simulated internal module crash!")


class SafeModule(BaseModule):
    def __init__(self):
        super().__init__(
            ModuleMetadata(
                id="safe_mod",
                name="Safe Module",
                supported_events=["CHAT_MESSAGE"],
            )
        )
        self.received_events = []

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        self.received_events.append(event_data)


@pytest.mark.asyncio
async def test_module_crash_is_isolated_and_does_not_crash_manager():
    registry = ModuleRegistry()
    crash_mod = CrashingModule()
    safe_mod = SafeModule()

    registry.register(crash_mod)
    registry.register(safe_mod)

    manager = ModuleManager(registry=registry)
    await manager.start_all()

    # Dispatch event
    await manager._dispatch_event("CHAT_MESSAGE", {"stream_id": "stream_1", "text": "Hello"})

    # Crashing module must enter FAILED state
    assert crash_mod.status == ModuleStatus.FAILED
    assert "Simulated internal module crash!" in crash_mod.get_health().last_error

    # Safe module must have processed the event normally!
    assert safe_mod.status == ModuleStatus.RUNNING
    assert len(safe_mod.received_events) == 1
