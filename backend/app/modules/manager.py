"""
Central Module Manager for GODDESS AI 2.0.

Orchestrates module discovery, dependency resolution, lifecycle state transitions,
failure isolation, and safe event distribution across all pluggable extensions.
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.models import (
    ModuleHealthStatus,
    ModuleInfo,
    ModuleStatus,
    StreamModuleConfig,
)
from app.modules.registry import ModuleRegistry, module_registry

logger = get_logger("modules.manager")


class ModuleManager:
    """Central orchestrator managing pluggable module lifecycles and event isolation."""

    def __init__(self, registry: Optional[ModuleRegistry] = None):
        self.registry = registry or module_registry
        self._subscribed_events: set[str] = set()
        self._is_initialized = False

    def register_module(self, module: BaseModule) -> None:
        """Register a module with the registry and subscribe to its declared events."""
        self.registry.register(module)
        self._ensure_event_subscriptions(module)
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                asyncio.create_task(event_bus.publish("MODULE_REGISTERED", {"module_id": module.module_id}))
        except RuntimeError:
            pass  # No running event loop at import time

    def _ensure_event_subscriptions(self, module: BaseModule) -> None:
        """Subscribe manager to EventBus events declared by the module."""
        for event_name in module.metadata.supported_events:
            if event_name not in self._subscribed_events:
                # EventBus handler dispatches to all subscribed modules with failure isolation
                event_bus.subscribe(event_name, self._create_isolated_dispatcher(event_name))
                self._subscribed_events.add(event_name)
                logger.debug(f"ModuleManager subscribed to EventBus event '{event_name}'.")

    def _create_isolated_dispatcher(self, event_name: str):
        """Create an async event handler that dispatches events with strict failure isolation."""
        async def dispatcher(event_data: Dict[str, Any]) -> None:
            await self._dispatch_event(event_name, event_data)
        return dispatcher

    async def _dispatch_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """
        Deliver event to all registered, running modules that support this event.
        Strict failure isolation ensures one module's crash never affects others or the core platform.
        """
        for module in self.registry.list_all():
            if module.is_running and event_name in module.metadata.supported_events:
                try:
                    await module.handle_event(event_name, event_data)
                except Exception as exc:
                    logger.error(
                        f"Unhandled exception in module '{module.module_id}' during event '{event_name}': {exc}",
                        exc_info=True,
                    )
                    module.mark_failed(str(exc))
                    await event_bus.publish(
                        "MODULE_FAILED",
                        {
                            "module_id": module.module_id,
                            "event": event_name,
                            "error": str(exc),
                        },
                    )

    async def load_all(self) -> None:
        """Load all registered modules in topological dependency order."""
        ordered = self.registry.resolve_dependency_order()
        for module in ordered:
            if module.status == ModuleStatus.REGISTERED:
                try:
                    await module.load()
                    await event_bus.publish("MODULE_LOADED", {"module_id": module.module_id})
                except Exception as exc:
                    logger.error(f"Failed to load module '{module.module_id}': {exc}")

    async def start_all(self) -> None:
        """Load and start all registered modules."""
        await self.load_all()
        for module in self.registry.list_all():
            if module.status in [ModuleStatus.LOADED, ModuleStatus.ENABLED, ModuleStatus.STOPPED]:
                try:
                    await module.start()
                    await event_bus.publish("MODULE_STARTED", {"module_id": module.module_id})
                except Exception as exc:
                    logger.error(f"Failed to start module '{module.module_id}': {exc}")

    async def stop_all(self) -> None:
        """Stop all running modules in reverse dependency order."""
        try:
            ordered = self.registry.resolve_dependency_order()
            ordered.reverse()
        except Exception:
            ordered = self.registry.list_all()

        for module in ordered:
            if module.is_running:
                try:
                    await module.stop()
                    await event_bus.publish("MODULE_STOPPED", {"module_id": module.module_id})
                except Exception as exc:
                    logger.warning(f"Error stopping module '{module.module_id}': {exc}")

    async def enable_module(self, module_id: str) -> BaseModule:
        """Enable a module."""
        module = self.registry.get(module_id)
        if module.status == ModuleStatus.REGISTERED:
            await module.load()
        await module.enable()
        await event_bus.publish("MODULE_ENABLED", {"module_id": module.module_id})
        return module

    async def disable_module(self, module_id: str) -> BaseModule:
        """Disable a module."""
        module = self.registry.get(module_id)
        await module.disable()
        await event_bus.publish("MODULE_DISABLED", {"module_id": module.module_id})
        return module

    async def start_module(self, module_id: str) -> BaseModule:
        """Start a module."""
        module = self.registry.get(module_id)
        if module.status == ModuleStatus.REGISTERED:
            await module.load()
        await module.start()
        await event_bus.publish("MODULE_STARTED", {"module_id": module.module_id})
        return module

    async def stop_module(self, module_id: str) -> BaseModule:
        """Stop a module."""
        module = self.registry.get(module_id)
        await module.stop()
        await event_bus.publish("MODULE_STOPPED", {"module_id": module.module_id})
        return module

    def get_module_info(self, module_id: str) -> ModuleInfo:
        """Fetch summary info and health for a module."""
        module = self.registry.get(module_id)
        return module.to_info()

    def list_modules(self) -> List[ModuleInfo]:
        """List summary info and health for all registered modules."""
        return [m.to_info() for m in self.registry.list_all()]

    def get_stream_config(self, module_id: str, stream_id: str) -> StreamModuleConfig:
        """Fetch stream-specific config for a module."""
        module = self.registry.get(module_id)
        return module.get_stream_config(stream_id)

    def update_stream_config(
        self, module_id: str, stream_id: str, config: StreamModuleConfig
    ) -> StreamModuleConfig:
        """Update stream-specific config for a module."""
        module = self.registry.get(module_id)
        return module.update_stream_config(stream_id, config)


# Global singleton module manager
module_manager = ModuleManager()
