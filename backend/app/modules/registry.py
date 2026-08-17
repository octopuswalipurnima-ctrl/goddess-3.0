"""
Module Registry and Dependency Graph Resolver for GODDESS AI 2.0.

Provides module registration, metadata validation, missing dependency detection,
and topological sorting for safe startup ordering with circular dependency prevention.
"""

from typing import Dict, List, Set

from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.exceptions import (
    CircularDependencyError,
    DuplicateModuleError,
    MissingDependencyError,
    ModuleNotFoundError,
)

logger = get_logger("modules.registry")


class ModuleRegistry:
    """Registry maintaining registered module instances and dependency relationships."""

    def __init__(self):
        self._modules: Dict[str, BaseModule] = {}

    def register(self, module: BaseModule) -> None:
        """Register a new module instance."""
        mod_id = module.module_id
        if mod_id in self._modules:
            raise DuplicateModuleError(f"Module with ID '{mod_id}' is already registered.")
        self._modules[mod_id] = module
        logger.info(f"Registered module '{mod_id}' (v{module.metadata.version}) in category '{module.metadata.category}'.")

    def unregister(self, module_id: str) -> BaseModule:
        """Unregister a module."""
        if module_id not in self._modules:
            raise ModuleNotFoundError(f"Module '{module_id}' is not registered.")
        module = self._modules.pop(module_id)
        logger.info(f"Unregistered module '{module_id}'.")
        return module

    def get(self, module_id: str) -> BaseModule:
        """Retrieve a registered module by ID."""
        if module_id not in self._modules:
            raise ModuleNotFoundError(f"Module '{module_id}' was not found in registry.")
        return self._modules[module_id]

    def has(self, module_id: str) -> bool:
        """Check if a module is registered."""
        return module_id in self._modules

    def list_all(self) -> List[BaseModule]:
        """List all registered modules."""
        return list(self._modules.values())

    def clear(self) -> None:
        """Clear all registered modules (useful for testing)."""
        self._modules.clear()

    def resolve_dependency_order(self) -> List[BaseModule]:
        """
        Validate dependencies and return modules in topological order.
        Raises MissingDependencyError if a required module is missing.
        Raises CircularDependencyError if a cycle is detected.
        """
        # 1. Check for missing dependencies
        for mod_id, module in self._modules.items():
            for dep_id in module.metadata.dependencies:
                if dep_id not in self._modules:
                    raise MissingDependencyError(
                        f"Module '{mod_id}' requires dependency '{dep_id}', which is not registered."
                    )

        # 2. Cycle detection and topological sort via DFS
        visited: Set[str] = set()
        visiting: Set[str] = set()
        order: List[BaseModule] = []

        def dfs(curr_id: str, path: List[str]) -> None:
            if curr_id in visiting:
                cycle_str = " -> ".join(path + [curr_id])
                raise CircularDependencyError(f"Circular dependency detected: {cycle_str}")
            if curr_id in visited:
                return

            visiting.add(curr_id)
            curr_mod = self._modules[curr_id]

            for dep_id in curr_mod.metadata.dependencies:
                dfs(dep_id, path + [curr_id])

            visiting.remove(curr_id)
            visited.add(curr_id)
            order.append(curr_mod)

        for mod_id in list(self._modules.keys()):
            if mod_id not in visited:
                dfs(mod_id, [])

        return order


# Global singleton registry instance
module_registry = ModuleRegistry()
