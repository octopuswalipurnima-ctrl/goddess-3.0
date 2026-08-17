"""
Tests for BaseModule and Metadata validation in GODDESS AI 2.0.
"""

import pytest
from pydantic import ValidationError

from app.modules.base import BaseModule
from app.modules.exceptions import InvalidStateTransitionError
from app.modules.models import (
    ModuleCapability,
    ModuleMetadata,
    ModuleStatus,
    StreamModuleConfig,
)


class DummyModule(BaseModule):
    def __init__(self, mod_id="dummy", deps=None, caps=None, events=None):
        meta = ModuleMetadata(
            id=mod_id,
            name="Dummy Test Module",
            version="1.0.0",
            description="Testing base module contract",
            author="Tester",
            dependencies=deps or [],
            capabilities=caps or [ModuleCapability.CHAT_READ],
            supported_events=events or ["CHAT_MESSAGE"],
        )
        super().__init__(meta)
        self.handled_events = []

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        self.handled_events.append((event_name, event_data))


def test_module_metadata_validation():
    # Valid metadata
    meta = ModuleMetadata(id="valid_mod-123", name="Valid")
    assert meta.id == "valid_mod-123"

    # Invalid ID with spaces or special characters
    with pytest.raises(ValidationError):
        ModuleMetadata(id="invalid mod ID!", name="Invalid")


@pytest.mark.asyncio
async def test_base_module_initial_state_and_config():
    mod = DummyModule(mod_id="test_base")
    assert mod.status == ModuleStatus.REGISTERED
    assert not mod.is_enabled
    assert not mod.is_running

    # Stream config isolation
    cfg_a = mod.get_stream_config("stream_1")
    assert not cfg_a.enabled
    mod.update_stream_config("stream_1", StreamModuleConfig(enabled=True, settings={"key": "val"}))
    assert mod.get_stream_config("stream_1").enabled is True
    assert mod.get_stream_config("stream_2").enabled is False
