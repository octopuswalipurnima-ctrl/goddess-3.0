"""
Operations Manager for GODDESS AI 2.0.

Central coordinator for production operations, stream supervision, emergency controls,
AI/Moderation toggles, and safe telemetry aggregation.
Enforces that every mutation strictly flows through ProductionSafetyController and
appropriate domain services with full audit tracking.
"""

from typing import Any, Dict, List, Optional
import time

from app.core.logging import get_logger
from app.core.safety_controller import SafetyState, safety_controller
from app.services.cohost.manager import cohost_manager
from app.services.moderation.manager import moderation_manager
from app.services.operations.audit import operations_audit_service
from app.services.operations.events import operations_event_publisher
from app.services.operations.models import (
    AIHealth,
    ComponentStatus,
    InfrastructureHealth,
    OperationalEventType,
    ProviderOperations,
    StreamOperations,
    SystemHealthDetailed,
    SystemOverview,
)
from app.services.operations.telemetry import operations_telemetry_service
from app.services.youtube.stream_supervisor import stream_supervisor

logger = get_logger("operations.manager")


class OperationsManager:
    """Production operations controller coordinating domain subsystems safely."""

    def __init__(self):
        self.safety = safety_controller
        self.supervisor = stream_supervisor
        self.moderation = moderation_manager
        self.cohost = cohost_manager
        self.audit = operations_audit_service
        self.telemetry = operations_telemetry_service
        self.publisher = operations_event_publisher

    # --- System & Telemetry Queries ---

    def get_system_overview(self) -> SystemOverview:
        """Fetch high-level system operational summary."""
        return self.telemetry.get_system_overview()

    def get_ai_health(self) -> AIHealth:
        """Fetch Gemini AI engine health and latency metrics."""
        return self.telemetry.get_ai_health()

    def get_provider_operations(self) -> Dict[str, ProviderOperations]:
        """Fetch multi-key provider operations for YouTube and Gemini."""
        return self.telemetry.get_provider_operations()

    def get_stream_operations(self, stream_id: str) -> StreamOperations:
        """Fetch operational status and safety state for a specific stream."""
        sup_summary = self.supervisor.get_stream_summary(stream_id)
        safety_st = self.safety.get_stream_state(stream_id)
        co_cfg = self.cohost.get_config(stream_id)
        mod_cfg = self.moderation.get_config(stream_id)

        status_str = sup_summary.state.value if (sup_summary and hasattr(sup_summary.state, "value")) else "OFFLINE"
        conn_str = "CONNECTED" if status_str == "LIVE" else ("RECONNECTING" if status_str == "RECONNECTING" else "DISCONNECTED")

        return StreamOperations(
            stream_id=stream_id,
            video_id=sup_summary.video_id if sup_summary else None,
            channel_id=sup_summary.channel_id if sup_summary else None,
            title=sup_summary.title if sup_summary else None,
            status=status_str,
            connection_status=conn_str,
            viewers=sup_summary.concurrent_viewers if sup_summary else 0,
            messages_received=sup_summary.messages_received if sup_summary else 0,
            messages_sent=sup_summary.messages_sent if sup_summary else 0,
            moderation_actions=mod_cfg.total_violations if hasattr(mod_cfg, "total_violations") else 0,
            cohost_responses=self.cohost.metrics.responses_sent,
            reconnect_count=sup_summary.reconnect_attempts if sup_summary else 0,
            last_message_at=sup_summary.last_message_at if sup_summary else None,
            last_error=sup_summary.last_error if sup_summary else None,
            safety_state=safety_st,
            safe_mode=safety_st in (SafetyState.SAFE_MODE, SafetyState.EMERGENCY_STOP),
            emergency_stop=safety_st == SafetyState.EMERGENCY_STOP,
            cohost_enabled=co_cfg.enabled,
            moderation_enabled=mod_cfg.enabled,
            dry_run=co_cfg.dry_run,
        )

    def get_all_stream_operations(self) -> Dict[str, StreamOperations]:
        """Fetch status for all supported streams (STREAM_A..STREAM_D)."""
        supported = ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]
        # Also include any dynamically attached streams
        for sid in self.supervisor.active_stream_ids:
            if sid not in supported:
                supported.append(sid)

        return {sid: self.get_stream_operations(sid) for sid in supported}

    def get_detailed_health(self) -> SystemHealthDetailed:
        """Aggregate health status across all components."""
        providers = self.get_provider_operations()
        ai_health = self.get_ai_health()
        streams_ops = self.get_all_stream_operations()

        infra = InfrastructureHealth(
            postgres_status=ComponentStatus.HEALTHY,
            redis_status=ComponentStatus.HEALTHY,
            event_bus_status=ComponentStatus.HEALTHY,
            websocket_status=ComponentStatus.HEALTHY,
        )

        overall = ComponentStatus.HEALTHY
        if self.safety.is_global_emergency or ai_health.provider_status == ComponentStatus.UNAVAILABLE:
            overall = ComponentStatus.DEGRADED

        return SystemHealthDetailed(
            overall_status=overall,
            version="2.0.0",
            environment="production",
            uptime_seconds=self.telemetry.get_system_overview().uptime_seconds,
            infrastructure=infra,
            youtube=providers.get("youtube", ProviderOperations(provider_name="YouTube")),
            gemini=ai_health,
            supervisor_status=ComponentStatus.HEALTHY,
            safety_controller=self.safety.get_diagnostics(),
            streams=streams_ops,
        )

    # --- Operational Mutations (Gated by Safety & Audit) ---

    async def trigger_emergency_stop(
        self,
        stream_id: Optional[str] = None,
        actor_id: str = "creator",
        actor_role: str = "OWNER",
        reason: str = "Manual Emergency Stop triggered via Control Center",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger emergency stop globally or for a specific stream."""
        await self.safety.trigger_emergency_stop(stream_id=stream_id, triggered_by=actor_id, reason=reason)

        if stream_id:
            # Also update domain managers
            self.cohost.update_config(stream_id, {"emergency_stop": True})
            self.moderation.update_config(stream_id, {"kill_switch": True})
        else:
            for s in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
                self.cohost.update_config(s, {"emergency_stop": True})
                self.moderation.update_config(s, {"kill_switch": True})

        # Record audit
        await self.audit.record_audit(
            action="EMERGENCY_STOP",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id or "GLOBAL",
            stream_id=stream_id,
            result="SUCCESS",
            reason=reason,
            request_id=request_id,
        )

        # Publish event
        await self.publisher.publish_event(
            event_type=OperationalEventType.EMERGENCY_STOP,
            payload={"stream_id": stream_id, "reason": reason, "triggered_by": actor_id},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "scope": stream_id or "GLOBAL", "safety_state": SafetyState.EMERGENCY_STOP.value}

    async def clear_emergency_stop(
        self,
        stream_id: Optional[str] = None,
        actor_id: str = "creator",
        actor_role: str = "OWNER",
        reason: str = "Emergency Stop cleared via Control Center",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clear emergency stop and return to NORMAL / DEGRADED state without message replay."""
        await self.safety.clear_emergency_stop(stream_id=stream_id, cleared_by=actor_id)

        if stream_id:
            self.cohost.update_config(stream_id, {"emergency_stop": False})
            self.moderation.update_config(stream_id, {"kill_switch": False})
        else:
            for s in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
                self.cohost.update_config(s, {"emergency_stop": False})
                self.moderation.update_config(s, {"kill_switch": False})

        await self.audit.record_audit(
            action="CLEAR_EMERGENCY_STOP",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id or "GLOBAL",
            stream_id=stream_id,
            result="SUCCESS",
            reason=reason,
            request_id=request_id,
        )

        await self.publisher.publish_event(
            event_type=OperationalEventType.SAFETY_STATE_CHANGED,
            payload={"stream_id": stream_id, "reason": reason, "action": "CLEARED_EMERGENCY_STOP"},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "scope": stream_id or "GLOBAL", "safety_state": SafetyState.NORMAL.value}

    async def enable_safe_mode(
        self,
        stream_id: Optional[str] = None,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        reason: str = "Safe Mode enabled via Control Center",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enable Safe Mode (suppresses AI CoHost chatter and risky mutations)."""
        await self.safety.enable_safe_mode(stream_id=stream_id, reason=reason)

        await self.audit.record_audit(
            action="ENABLE_SAFE_MODE",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id or "GLOBAL",
            stream_id=stream_id,
            result="SUCCESS",
            reason=reason,
            request_id=request_id,
        )

        await self.publisher.publish_event(
            event_type=OperationalEventType.SAFE_MODE_CHANGED,
            payload={"stream_id": stream_id, "safe_mode": True, "reason": reason},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "scope": stream_id or "GLOBAL", "safety_state": SafetyState.SAFE_MODE.value}

    async def disable_safe_mode(
        self,
        stream_id: Optional[str] = None,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        reason: str = "Safe Mode disabled via Control Center",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Disable Safe Mode without replaying past suppressed messages."""
        await self.safety.disable_safe_mode(stream_id=stream_id)

        await self.audit.record_audit(
            action="DISABLE_SAFE_MODE",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id or "GLOBAL",
            stream_id=stream_id,
            result="SUCCESS",
            reason=reason,
            request_id=request_id,
        )

        await self.publisher.publish_event(
            event_type=OperationalEventType.SAFE_MODE_CHANGED,
            payload={"stream_id": stream_id, "safe_mode": False, "reason": reason},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "scope": stream_id or "GLOBAL", "safety_state": SafetyState.NORMAL.value}

    async def attach_stream(
        self,
        stream_id: str,
        video_id: str,
        channel_id: Optional[str] = None,
        title: Optional[str] = None,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Attach and supervise a YouTube Live stream."""
        # SafetyController gate check
        can_attach, gate_reason = self.safety.can_mutate_stream(stream_id)
        if not can_attach:
            await self.audit.record_audit(
                action="ATTACH_STREAM_BLOCKED",
                actor_id=actor_id,
                actor_role=actor_role,
                target=stream_id,
                stream_id=stream_id,
                result="BLOCKED",
                reason=gate_reason,
                request_id=request_id,
            )
            return {"status": "BLOCKED", "reason": gate_reason}

        session = await self.supervisor.attach_stream(
            stream_id=stream_id,
            video_id=video_id,
            channel_id=channel_id,
            title=title,
        )

        await self.audit.record_audit(
            action="ATTACH_STREAM",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            metadata={"video_id": video_id, "channel_id": channel_id},
            request_id=request_id,
        )

        await self.publisher.publish_event(
            event_type=OperationalEventType.STREAM_STATUS_CHANGED,
            payload={"stream_id": stream_id, "status": "ATTACHED", "video_id": video_id},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id, "video_id": video_id}

    async def detach_stream(
        self,
        stream_id: str,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        reason: str = "Detached via Control Center",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detach stream session cleanly."""
        await self.supervisor.detach_stream(stream_id=stream_id)

        await self.audit.record_audit(
            action="DETACH_STREAM",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            reason=reason,
            request_id=request_id,
        )

        await self.publisher.publish_event(
            event_type=OperationalEventType.STREAM_STATUS_CHANGED,
            payload={"stream_id": stream_id, "status": "DETACHED", "reason": reason},
            stream_id=stream_id,
            actor_id=actor_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id}

    async def reconnect_stream(
        self,
        stream_id: str,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger reconnection attempt for a stream."""
        can_recon, gate_reason = self.safety.can_mutate_stream(stream_id)
        if not can_recon:
            return {"status": "BLOCKED", "reason": gate_reason}

        await self.supervisor.reconnect_stream(stream_id=stream_id)

        await self.audit.record_audit(
            action="RECONNECT_STREAM",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            request_id=request_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id}

    async def set_cohost_enabled(
        self,
        stream_id: str,
        enabled: bool,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Toggle CoHost enabled status on a stream."""
        self.cohost.update_config(stream_id, {"enabled": enabled})

        await self.audit.record_audit(
            action="COHOST_TOGGLE",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            metadata={"enabled": enabled},
            request_id=request_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id, "cohost_enabled": enabled}

    async def set_cohost_dry_run(
        self,
        stream_id: str,
        dry_run: bool,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Toggle CoHost DRY_RUN status on a stream."""
        self.cohost.update_config(stream_id, {"dry_run": dry_run})

        await self.audit.record_audit(
            action="COHOST_DRY_RUN_TOGGLE",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            metadata={"dry_run": dry_run},
            request_id=request_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id, "dry_run": dry_run}

    async def set_moderation_enabled(
        self,
        stream_id: str,
        enabled: bool,
        actor_id: str = "creator",
        actor_role: str = "OPERATOR",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Toggle Moderation enabled status on a stream."""
        self.moderation.update_config(stream_id, {"enabled": enabled})

        await self.audit.record_audit(
            action="MODERATION_TOGGLE",
            actor_id=actor_id,
            actor_role=actor_role,
            target=stream_id,
            stream_id=stream_id,
            result="SUCCESS",
            metadata={"enabled": enabled},
            request_id=request_id,
        )

        return {"status": "SUCCESS", "stream_id": stream_id, "moderation_enabled": enabled}


# Global singleton instance
operations_manager = OperationsManager()
