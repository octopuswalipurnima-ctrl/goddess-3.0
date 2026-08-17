"""
Tests for Module dependency resolution and cycle detection.
"""

import pytest

from app.modules.base import BaseModule
from app.modules.exceptions import (
    CircularDependencyError,
    MissingDependencyError,
)
from app.modules.models import ModuleMetadata
from app.modules.registry import ModuleRegistry


class DepModule(BaseModule):
    def __init__(self, mod_id: str, deps: list[str]):
        super().__init__(ModuleMetadata(id=mod_id, name=f"Module {mod_id}", dependencies=deps))

    async def handle_event(self, event_name: str, event_data: dict) -> None:
        pass


def test_dependency_resolution_topological_order():
    registry = ModuleRegistry()
    # A has no deps
    # B depends on A
    # C depends on B
    ma = DepModule("a", [])
    mb = DepModule("b", ["a"])
    mc = DepModule("c", ["b"])

    registry.register(mc)
    registry.register(ma)
    registry.register(mb)

    ordered = registry.resolve_dependency_order()
    ordered_ids = [m.module_id for m in ordered]

    # 'a' must come before 'b', 'b' must come before 'c'
    assert ordered_ids.index("a") < ordered_ids.index("b")
    assert ordered_ids.index("b") < ordered_ids.index("c")


def test_missing_dependency_raises():
    registry = ModuleRegistry()
    mb = DepModule("b", ["missing_dep_x"])
    registry.register(mb)

    with pytest.raises(MissingDependencyError) as exc_info:
        registry.resolve_dependency_order()
    assert "missing_dep_x" in str(exc_info.value)


def test_circular_dependency_raises():
    registry = ModuleRegistry()
    # Cycle: A -> B -> C -> A
    ma = DepModule("a", ["b"])
    mb = DepModule("b", ["c"])
    mc = DepModule("c", ["a"])

    registry.register(ma)
    registry.register(mb)
    registry.register(mc)

    with pytest.raises(CircularDependencyError) as exc_info:
        registry.resolve_dependency_order()
    assert "Circular dependency detected" in str(exc_info.value)
