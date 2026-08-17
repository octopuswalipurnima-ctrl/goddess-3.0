"""
Tests for Module lifecycle state transitions and execution.
"""

import pytest

from app.modules.base import BaseModule
from app.modules.exceptions import InvalidStateTransitionError
from app.modules.models import ModuleMetadata, ModuleStatus


class LifecycleTestModule(BaseModule):
    def __init__(self):
        super().__init__(ModuleMetadata(id="lifecycle_mod", name="Lifecycle Test"))
        self.initialized = False
        self.started = False
        self.stopped = False

    async def initialize(self) -> None:
        self.initialized = True

    async def on_start(self) -> None:
        self.started = True

    async def on_stop(self) -> None:
        self.stopped = True

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        pass


@pytest.mark.asyncio
async def test_module_valid_lifecycle_transitions():
    mod = LifecycleTestModule()
    assert mod.status == ModuleStatus.REGISTERED

    # REGISTERED -> LOADED
    await mod.load()
    assert mod.status == ModuleStatus.LOADED
    assert mod.initialized is True

    # LOADED -> ENABLED
    await mod.enable()
    assert mod.status == ModuleStatus.ENABLED
    assert mod.is_enabled is True

    # ENABLED -> RUNNING
    await mod.start()
    assert mod.status == ModuleStatus.RUNNING
    assert mod.is_running is True
    assert mod.started is True

    # RUNNING -> STOPPED
    await mod.stop()
    assert mod.status == ModuleStatus.STOPPED
    assert not mod.is_running
    assert mod.stopped is True

    # STOPPED -> DISABLED
    await mod.disable()
    assert mod.status == ModuleStatus.DISABLED
    assert not mod.is_enabled


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition_raises():
    mod = LifecycleTestModule()
    # Cannot jump directly from REGISTERED to STOPPED
    with pytest.raises(InvalidStateTransitionError):
        mod._transition_to(ModuleStatus.STOPPED)
