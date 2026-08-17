"""
Base Module Contract and Lifecycle State Machine for GODDESS AI 2.0.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.modules.exceptions import InvalidStateTransitionError, ModuleExecutionError
from app.modules.models import (
    ModuleCapability,
    ModuleHealth,
    ModuleHealthStatus,
    ModuleInfo,
    ModuleMetadata,
    ModuleStatus,
    StreamModuleConfig,
)

logger = get_logger("modules.base")

# Valid lifecycle state transitions map
VALID_TRANSITIONS = {
    ModuleStatus.DISCOVERED: {ModuleStatus.REGISTERED, ModuleStatus.FAILED},
    ModuleStatus.REGISTERED: {ModuleStatus.LOADED, ModuleStatus.FAILED},
    ModuleStatus.LOADED: {ModuleStatus.ENABLED, ModuleStatus.DISABLED, ModuleStatus.FAILED},
    ModuleStatus.ENABLED: {ModuleStatus.RUNNING, ModuleStatus.DISABLED, ModuleStatus.FAILED},
    ModuleStatus.RUNNING: {ModuleStatus.STOPPED, ModuleStatus.FAILED},
    ModuleStatus.STOPPED: {ModuleStatus.RUNNING, ModuleStatus.DISABLED, ModuleStatus.FAILED},
    ModuleStatus.DISABLED: {ModuleStatus.ENABLED, ModuleStatus.FAILED},
    ModuleStatus.FAILED: {ModuleStatus.LOADED, ModuleStatus.DISABLED, ModuleStatus.REGISTERED},
}


class BaseModule(ABC):
    """
    Abstract Base Class for all GODDESS AI 2.0 pluggable modules.
    Enforces strict lifecycle state transitions, permission declarations,
    health reporting, and isolated per-stream configuration.
    """

    def __init__(self, metadata: ModuleMetadata):
        self.metadata = metadata
        self._status = ModuleStatus.REGISTERED
        self._health = ModuleHealth()
        self._load_time: Optional[str] = None
        # stream_id -> StreamModuleConfig
        self._stream_configs: Dict[str, StreamModuleConfig] = {}

    @property
    def module_id(self) -> str:
        return self.metadata.id

    @property
    def status(self) -> ModuleStatus:
        return self._status

    @property
    def is_enabled(self) -> bool:
        return self._status in [ModuleStatus.ENABLED, ModuleStatus.RUNNING]

    @property
    def is_running(self) -> bool:
        return self._status == ModuleStatus.RUNNING

    def _transition_to(self, target_status: ModuleStatus) -> None:
        """Validate and apply a lifecycle state transition."""
        allowed = VALID_TRANSITIONS.get(self._status, set())
        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Module '{self.module_id}' cannot transition from '{self._status.value}' to '{target_status.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )
        old_status = self._status
        self._status = target_status
        logger.debug(f"Module '{self.module_id}' transitioned: {old_status.value} -> {target_status.value}")

    def mark_failed(self, error_message: str) -> None:
        """Record an unhandled failure without crashing the platform."""
        self._status = ModuleStatus.FAILED
        self._health.status = ModuleHealthStatus.ERROR
        self._health.details = f"Module failed: {error_message}"
        self._health.last_error = error_message
        self._health.last_error_time = datetime.now(timezone.utc).isoformat()
        logger.error(f"Module '{self.module_id}' entered FAILED state: {error_message}")

    # --- Lifecycle Methods ---

    async def load(self) -> None:
        """Load module resources and initialize state."""
        try:
            await self.initialize()
            self._load_time = datetime.now(timezone.utc).isoformat()
            self._transition_to(ModuleStatus.LOADED)
        except Exception as exc:
            self.mark_failed(str(exc))
            raise ModuleExecutionError(f"Failed to load module '{self.module_id}': {exc}") from exc

    async def enable(self) -> None:
        """Enable module globally."""
        try:
            await self.on_enable()
            self._transition_to(ModuleStatus.ENABLED)
        except Exception as exc:
            self.mark_failed(str(exc))
            raise ModuleExecutionError(f"Failed to enable module '{self.module_id}': {exc}") from exc

    async def disable(self) -> None:
        """Disable module globally."""
        try:
            if self.is_running:
                await self.stop()
            await self.on_disable()
            self._transition_to(ModuleStatus.DISABLED)
        except Exception as exc:
            self.mark_failed(str(exc))
            raise ModuleExecutionError(f"Failed to disable module '{self.module_id}': {exc}") from exc

    async def start(self) -> None:
        """Start module active processing loops or listeners."""
        if not self.is_enabled:
            await self.enable()
        try:
            await self.on_start()
            self._transition_to(ModuleStatus.RUNNING)
        except Exception as exc:
            self.mark_failed(str(exc))
            raise ModuleExecutionError(f"Failed to start module '{self.module_id}': {exc}") from exc

    async def stop(self) -> None:
        """Stop module active processing loops."""
        try:
            await self.on_stop()
            self._transition_to(ModuleStatus.STOPPED)
        except Exception as exc:
            self.mark_failed(str(exc))
            raise ModuleExecutionError(f"Failed to stop module '{self.module_id}': {exc}") from exc

    async def unload(self) -> None:
        """Clean up all resources upon module unregistration."""
        try:
            if self.is_running:
                await self.stop()
            if self.is_enabled:
                await self.disable()
            await self.on_unload()
        except Exception as exc:
            logger.warning(f"Error during module '{self.module_id}' unload: {exc}")

    # --- Hook Methods for Concrete Modules ---

    async def initialize(self) -> None:
        """Override to load dependencies, schemas, or initial setup."""
        pass

    async def on_enable(self) -> None:
        """Override for actions when module is enabled."""
        pass

    async def on_disable(self) -> None:
        """Override for actions when module is disabled."""
        pass

    async def on_start(self) -> None:
        """Override for actions when module begins running."""
        pass

    async def on_stop(self) -> None:
        """Override for actions when module stops running."""
        pass

    async def on_unload(self) -> None:
        """Override for teardown and resource cleanup."""
        pass

    @abstractmethod
    async def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Handle incoming EventBus event in an isolated manner."""
        pass

    # --- Configuration and Diagnostics ---

    def get_health(self) -> ModuleHealth:
        """Return current module health."""
        return self._health

    def get_stream_config(self, stream_id: str) -> StreamModuleConfig:
        """Retrieve per-stream module configuration."""
        if stream_id not in self._stream_configs:
            self._stream_configs[stream_id] = StreamModuleConfig(enabled=False)
        return self._stream_configs[stream_id]

    def update_stream_config(self, stream_id: str, config: StreamModuleConfig) -> StreamModuleConfig:
        """Update per-stream module configuration."""
        self._stream_configs[stream_id] = config
        logger.info(f"Updated stream '{stream_id}' config for module '{self.module_id}': Enabled={config.enabled}")
        return config

    def to_info(self) -> ModuleInfo:
        """Export public status and diagnostics summary."""
        active_streams = [s for s, c in self._stream_configs.items() if c.enabled]
        return ModuleInfo(
            metadata=self.metadata,
            status=self._status,
            enabled=self.is_enabled,
            health=self._health,
            load_time=self._load_time,
            active_streams=active_streams,
        )
