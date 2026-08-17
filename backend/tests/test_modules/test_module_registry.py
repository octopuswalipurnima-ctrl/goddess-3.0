"""
Tests for ModuleRegistry operations.
"""

import pytest

from app.modules.base import BaseModule
from app.modules.exceptions import (
    DuplicateModuleError,
    ModuleNotFoundError,
)
from app.modules.models import ModuleMetadata
from app.modules.registry import ModuleRegistry


class SampleModule(BaseModule):
    def __init__(self, mod_id: str):
        super().__init__(ModuleMetadata(id=mod_id, name=f"Module {mod_id}"))

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        pass


def test_registry_register_and_get():
    registry = ModuleRegistry()
    m1 = SampleModule("mod_1")
    registry.register(m1)

    assert registry.has("mod_1") is True
    assert registry.get("mod_1") == m1
    assert len(registry.list_all()) == 1


def test_registry_duplicate_registration_raises():
    registry = ModuleRegistry()
    m1 = SampleModule("mod_dup")
    registry.register(m1)

    with pytest.raises(DuplicateModuleError):
        registry.register(SampleModule("mod_dup"))


def test_registry_unregister():
    registry = ModuleRegistry()
    m1 = SampleModule("mod_unreg")
    registry.register(m1)
    unregistered = registry.unregister("mod_unreg")

    assert unregistered == m1
    assert registry.has("mod_unreg") is False

    with pytest.raises(ModuleNotFoundError):
        registry.get("mod_unreg")
