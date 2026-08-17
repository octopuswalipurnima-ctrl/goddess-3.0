"""
Module System for GODDESS AI 2.0.

Exports base module classes, lifecycle models, registry, manager, and built-in modules.
"""

from app.modules.base import BaseModule
from app.modules.commands import CommandsModule
from app.modules.exceptions import (
    CircularDependencyError,
    DuplicateModuleError,
    InvalidModuleMetadataError,
    InvalidStateTransitionError,
    MissingDependencyError,
    ModuleError,
    ModuleExecutionError,
    ModuleNotFoundError,
    PermissionDeniedError,
)
from app.modules.manager import ModuleManager, module_manager
from app.modules.models import (
    ModuleCapability,
    ModuleHealth,
    ModuleHealthStatus,
    ModuleInfo,
    ModuleMetadata,
    ModuleStatus,
    StreamModuleConfig,
)
from app.modules.registry import ModuleRegistry, module_registry
from app.modules.stream_stats import StreamStatsModule
from app.modules.viewer_interaction import ViewerInteractionModule
from app.modules.welcome import WelcomeModule


def register_builtin_modules(manager: ModuleManager = module_manager) -> None:
    """Register default built-in platform modules."""
    builtins = [
        CommandsModule(),
        WelcomeModule(),
        StreamStatsModule(),
        ViewerInteractionModule(),
    ]
    for mod in builtins:
        if not manager.registry.has(mod.module_id):
            manager.register_module(mod)


# Automatically register built-ins on package import
register_builtin_modules()

__all__ = [
    "BaseModule",
    "ModuleMetadata",
    "ModuleStatus",
    "ModuleCapability",
    "ModuleHealth",
    "ModuleHealthStatus",
    "ModuleInfo",
    "StreamModuleConfig",
    "ModuleError",
    "ModuleNotFoundError",
    "DuplicateModuleError",
    "InvalidModuleMetadataError",
    "InvalidStateTransitionError",
    "MissingDependencyError",
    "CircularDependencyError",
    "ModuleExecutionError",
    "PermissionDeniedError",
    "ModuleRegistry",
    "module_registry",
    "ModuleManager",
    "module_manager",
    "CommandsModule",
    "WelcomeModule",
    "StreamStatsModule",
    "ViewerInteractionModule",
    "register_builtin_modules",
]
