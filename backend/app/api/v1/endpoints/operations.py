"""
Creator Control Center Operations REST API for GODDESS AI 2.0.

Provides authenticated and RBAC-governed endpoints for stream controls, emergency stops,
safe mode gates, AI diagnostics, provider telemetry, and operational audit logs.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_permission
from app.auth.models import UserSchema
from app.services.operations import (
    AIHealth,
    AuditEvent,
    OperationalEvent,
    ProviderOperations,
    StreamOperations,
    SystemOverview,
    operations_audit_service,
    operations_event_publisher,
    operations_manager,
)

router = APIRouter(prefix="/operations", tags=["Creator Control Center Operations"])


class StreamAttachRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=50)
    channel_id: Optional[str] = None
    title: Optional[str] = None


class EmergencyStopRequest(BaseModel):
    reason: str = Field(default="Emergency Stop triggered via Creator Control Center", max_length=300)


class SafeModeRequest(BaseModel):
    reason: str = Field(default="Safe Mode toggled via Creator Control Center", max_length=300)


class DryRunToggleRequest(BaseModel):
    dry_run: bool = True


# --- Telemetry & Overview Queries ---

@router.get(
    "/overview",
    response_model=SystemOverview,
    dependencies=[Depends(require_permission("system.read"))],
    summary="Get System Overview",
)
async def get_system_overview():
    """Retrieve operational system overview, active stream counts, and safety state."""
    return operations_manager.get_system_overview()


@router.get(
    "/system",
    response_model=SystemOverview,
    dependencies=[Depends(require_permission("system.read"))],
    summary="Get System Telemetry",
)
async def get_system_telemetry():
    """Retrieve system telemetry overview."""
    return operations_manager.get_system_overview()


@router.get(
    "/streams",
    response_model=Dict[str, StreamOperations],
    dependencies=[Depends(require_permission("stream.read"))],
    summary="Get All Stream Operations",
)
async def get_all_streams():
    """Fetch operational and safety state for all streams (STREAM_A..STREAM_D)."""
    return operations_manager.get_all_stream_operations()


@router.get(
    "/streams/{stream_id}",
    response_model=StreamOperations,
    dependencies=[Depends(require_permission("stream.read"))],
    summary="Get Single Stream Operations",
)
async def get_single_stream(stream_id: str):
    """Fetch operational state for a specific stream."""
    return operations_manager.get_stream_operations(stream_id)


@router.get(
    "/ai",
    response_model=AIHealth,
    dependencies=[Depends(require_permission("ai.read"))],
    summary="Get AI Operations Health",
)
async def get_ai_health():
    """Fetch Gemini AI engine health, credential pool status, and latency percentiles."""
    return operations_manager.get_ai_health()


@router.get(
    "/providers",
    response_model=Dict[str, ProviderOperations],
    dependencies=[Depends(require_permission("system.read"))],
    summary="Get Provider Operations Health",
)
async def get_provider_operations():
    """Fetch multi-key pool health for YouTube and Gemini providers with safe key aliases."""
    return operations_manager.get_provider_operations()


@router.get(
    "/audit",
    response_model=List[AuditEvent],
    dependencies=[Depends(require_permission("audit.read"))],
    summary="Get Operational Audit Log",
)
async def get_audit_log(
    stream_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Fetch secret-redacted audit events."""
    return operations_audit_service.get_recent_records(stream_id=stream_id, action=action, limit=limit)


@router.get(
    "/events",
    response_model=List[OperationalEvent],
    dependencies=[Depends(require_permission("system.read"))],
    summary="Get Recent Operational Events",
)
async def get_operational_events(
    stream_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Fetch recent bounded operational events."""
    return operations_event_publisher.get_recent_events(stream_id=stream_id, limit=limit)


# --- Stream Lifecycle Controls ---

@router.post(
    "/streams/{stream_id}/attach",
    dependencies=[Depends(require_permission("stream.attach"))],
    summary="Attach YouTube Stream",
)
async def attach_stream(
    stream_id: str,
    payload: StreamAttachRequest,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Supervise and attach a YouTube Live stream."""
    res = await operations_manager.attach_stream(
        stream_id=stream_id,
        video_id=payload.video_id,
        channel_id=payload.channel_id,
        title=payload.title,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )
    if res.get("status") == "BLOCKED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.get("reason"))
    return res


@router.post(
    "/streams/{stream_id}/detach",
    dependencies=[Depends(require_permission("stream.detach"))],
    summary="Detach YouTube Stream",
)
async def detach_stream(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Detach live stream session cleanly."""
    return await operations_manager.detach_stream(
        stream_id=stream_id,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/reconnect",
    dependencies=[Depends(require_permission("stream.reconnect"))],
    summary="Reconnect YouTube Stream",
)
async def reconnect_stream(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Trigger stream reconnect sequence."""
    res = await operations_manager.reconnect_stream(
        stream_id=stream_id,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )
    if res.get("status") == "BLOCKED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=res.get("reason"))
    return res


# --- Stream Safety Controls ---

@router.post(
    "/streams/{stream_id}/safe-mode/enable",
    dependencies=[Depends(require_permission("stream.safe_mode"))],
    summary="Enable Stream Safe Mode",
)
async def enable_stream_safe_mode(
    stream_id: str,
    payload: SafeModeRequest = SafeModeRequest(),
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Enable Safe Mode on a specific stream."""
    return await operations_manager.enable_safe_mode(
        stream_id=stream_id,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        reason=payload.reason,
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/safe-mode/disable",
    dependencies=[Depends(require_permission("stream.safe_mode"))],
    summary="Disable Stream Safe Mode",
)
async def disable_stream_safe_mode(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Disable Safe Mode on a specific stream without historical replay."""
    return await operations_manager.disable_safe_mode(
        stream_id=stream_id,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Stream Emergency Stop",
)
async def trigger_stream_emergency_stop(
    stream_id: str,
    payload: EmergencyStopRequest = EmergencyStopRequest(),
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Halt all outgoing chat and automated actions on a specific stream."""
    return await operations_manager.trigger_emergency_stop(
        stream_id=stream_id,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        reason=payload.reason,
        request_id=x_request_id,
    )


# --- Global Emergency Controls ---

@router.post(
    "/emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Global Emergency Stop",
)
async def trigger_global_emergency_stop(
    payload: EmergencyStopRequest = EmergencyStopRequest(),
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Immediately halt all automated actions and outgoing chat globally across all streams."""
    return await operations_manager.trigger_emergency_stop(
        stream_id=None,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        reason=payload.reason,
        request_id=x_request_id,
    )


@router.post(
    "/emergency-stop/clear",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Clear Global Emergency Stop",
)
async def clear_global_emergency_stop(
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Clear emergency stop globally without replaying suppressed messages."""
    return await operations_manager.clear_emergency_stop(
        stream_id=None,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/safe-mode/enable",
    dependencies=[Depends(require_permission("system.control"))],
    summary="Global Safe Mode Enable",
)
async def enable_global_safe_mode(
    payload: SafeModeRequest = SafeModeRequest(),
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Enable Safe Mode globally across all streams."""
    return await operations_manager.enable_safe_mode(
        stream_id=None,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        reason=payload.reason,
        request_id=x_request_id,
    )


@router.post(
    "/safe-mode/disable",
    dependencies=[Depends(require_permission("system.control"))],
    summary="Global Safe Mode Disable",
)
async def disable_global_safe_mode(
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Disable Safe Mode globally."""
    return await operations_manager.disable_safe_mode(
        stream_id=None,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


# --- AI & Moderation Operational Controls ---

@router.post(
    "/streams/{stream_id}/cohost/enable",
    dependencies=[Depends(require_permission("cohost.control"))],
    summary="Enable Stream CoHost",
)
async def enable_stream_cohost(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Enable CoHost on a stream."""
    return await operations_manager.set_cohost_enabled(
        stream_id=stream_id,
        enabled=True,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/cohost/disable",
    dependencies=[Depends(require_permission("cohost.control"))],
    summary="Disable Stream CoHost",
)
async def disable_stream_cohost(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Disable CoHost on a stream."""
    return await operations_manager.set_cohost_enabled(
        stream_id=stream_id,
        enabled=False,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/cohost/dry-run",
    dependencies=[Depends(require_permission("cohost.control"))],
    summary="Set CoHost Dry-Run Mode",
)
async def set_stream_cohost_dry_run(
    stream_id: str,
    payload: DryRunToggleRequest,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Toggle CoHost DRY_RUN mode."""
    return await operations_manager.set_cohost_dry_run(
        stream_id=stream_id,
        dry_run=payload.dry_run,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/moderation/enable",
    dependencies=[Depends(require_permission("moderation.control"))],
    summary="Enable Stream Moderation",
)
async def enable_stream_moderation(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Enable Moderation on a stream."""
    return await operations_manager.set_moderation_enabled(
        stream_id=stream_id,
        enabled=True,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )


@router.post(
    "/streams/{stream_id}/moderation/disable",
    dependencies=[Depends(require_permission("moderation.control"))],
    summary="Disable Stream Moderation",
)
async def disable_stream_moderation(
    stream_id: str,
    current_user: UserSchema = Depends(get_current_user),
    x_request_id: Optional[str] = Header(default=None),
):
    """Disable Moderation on a stream."""
    return await operations_manager.set_moderation_enabled(
        stream_id=stream_id,
        enabled=False,
        actor_id=current_user.username,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        request_id=x_request_id,
    )
