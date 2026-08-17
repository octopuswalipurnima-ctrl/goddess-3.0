"""
Autonomous Production Health Supervisor for GODDESS AI 2.0.

Continuously observes infrastructure, providers, and streams with bounded checks,
detects failure/recovery transitions, and publishes health telemetry with zero replay.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional

from app.core.circuit_breaker import circuit_breakers
from app.core.events import event_bus
from app.core.logging import get_logger
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.models import ComponentStatus

logger = get_logger("operations.health_supervisor")


class ProductionHealthSupervisor:
    """Continuous autonomous supervisor observing dependency health."""

    def __init__(self, check_interval_seconds: float = 10.0):
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_check_timestamp: Optional[float] = None
        self._overall_status = ComponentStatus.HEALTHY
        self._component_statuses: Dict[str, ComponentStatus] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def overall_status(self) -> ComponentStatus:
        return self._overall_status

    async def start(self, spawn_loop: bool = True) -> None:
        """Start the background autonomous health supervisor task."""
        if self._running:
            return
        self._running = True
        import os
        if spawn_loop and not os.getenv("PYTEST_CURRENT_TEST"):
            self._task = asyncio.create_task(self._supervisor_loop())
        logger.info(f"ProductionHealthSupervisor started (Interval: {self.check_interval_seconds}s).")

    async def stop(self) -> None:
        """Gracefully stop background supervisor task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ProductionHealthSupervisor stopped.")

    async def check_all_now(self) -> Dict[str, Any]:
        """Execute an immediate synchronous health sweep across all components."""
        self._last_check_timestamp = time.time()
        statuses: Dict[str, ComponentStatus] = {}

        # 1. Database
        from app.db.session import ping_database
        try:
            db_res = await ping_database()
            if db_res["status"] == "HEALTHY":
                statuses["database"] = ComponentStatus.HEALTHY
                circuit_breakers.get("postgres").record_success()
            elif db_res["status"] == "NOT_CONFIGURED":
                statuses["database"] = ComponentStatus.NOT_CONFIGURED
            else:
                statuses["database"] = ComponentStatus.UNAVAILABLE
                circuit_breakers.get("postgres").record_failure()
        except Exception:
            statuses["database"] = ComponentStatus.UNAVAILABLE
            circuit_breakers.get("postgres").record_failure()

        # 2. Redis
        from app.core.redis import redis_state
        try:
            r_res = await redis_state.ping()
            if r_res["status"] == "HEALTHY":
                statuses["redis"] = ComponentStatus.HEALTHY
                circuit_breakers.get("redis").record_success()
            elif r_res["status"] == "DEGRADED":
                statuses["redis"] = ComponentStatus.DEGRADED
            else:
                statuses["redis"] = ComponentStatus.UNAVAILABLE
        except Exception:
            statuses["redis"] = ComponentStatus.DEGRADED

        # 3. YouTube Credentials
        from app.services.youtube.credentials import youtube_credentials
        yt_summary = youtube_credentials.get_health_summary()
        yt_avail = sum(1 for c in yt_summary if c.state.value == "AVAILABLE")
        if yt_avail > 0:
            statuses["youtube"] = ComponentStatus.HEALTHY
        elif len(yt_summary) == 0:
            statuses["youtube"] = ComponentStatus.NOT_CONFIGURED
        else:
            statuses["youtube"] = ComponentStatus.UNAVAILABLE

        # 4. Gemini Credentials
        from app.services.gemini.credentials import gemini_credentials
        g_summary = gemini_credentials.get_health_summary()
        g_avail = sum(1 for c in g_summary if c.state.value == "AVAILABLE")
        if g_avail > 0:
            statuses["gemini"] = ComponentStatus.HEALTHY
        elif len(g_summary) == 0:
            statuses["gemini"] = ComponentStatus.NOT_CONFIGURED
        else:
            statuses["gemini"] = ComponentStatus.UNAVAILABLE

        # 5. Overall Evaluation
        if safety_controller.is_global_emergency:
            overall = ComponentStatus.DEGRADED
        elif (
            statuses.get("database") == ComponentStatus.UNAVAILABLE
            or statuses.get("gemini") == ComponentStatus.UNAVAILABLE
            or statuses.get("youtube") == ComponentStatus.UNAVAILABLE
        ):
            overall = ComponentStatus.DEGRADED
        else:
            overall = ComponentStatus.HEALTHY

        prev_overall = self._overall_status
        self._overall_status = overall
        self._component_statuses = statuses

        # Publish state change if overall status transitioned
        if prev_overall != overall:
            logger.info(f"System health transitioned from {prev_overall.value} to {overall.value}.")
            await event_bus.publish(
                "SYSTEM_HEALTH_CHANGED",
                {
                    "overall_status": overall.value,
                    "previous_status": prev_overall.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return {
            "overall_status": overall.value,
            "components": {k: v.value for k, v in statuses.items()},
            "circuit_breakers": circuit_breakers.get_all_diagnostics(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _supervisor_loop(self) -> None:
        while self._running:
            try:
                await self.check_all_now()
            except Exception as exc:
                logger.warning(f"Health supervisor sweep encountered non-fatal error: {exc}")
            await asyncio.sleep(self.check_interval_seconds)


# Global singleton
health_supervisor = ProductionHealthSupervisor()
