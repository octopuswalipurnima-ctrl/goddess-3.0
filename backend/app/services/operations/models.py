"""
Production Operations Domain Models for GODDESS AI 2.0.

Provides structured schemas for system overview, health telemetry, stream operations,
AI diagnostics, provider status, infrastructure health, and operational audit records.
Guarantees zero secret exposure and bounded resource representations.
"""

from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.safety_controller import SafetyState


class ComponentStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class OperationalEventType(str, Enum):
    SYSTEM_HEALTH_CHANGED = "SYSTEM_HEALTH_CHANGED"
    STREAM_STATUS_CHANGED = "STREAM_STATUS_CHANGED"
    SAFETY_STATE_CHANGED = "SAFETY_STATE_CHANGED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SAFE_MODE_CHANGED = "SAFE_MODE_CHANGED"
    PROVIDER_HEALTH_CHANGED = "PROVIDER_HEALTH_CHANGED"
    AI_HEALTH_CHANGED = "AI_HEALTH_CHANGED"
    AUDIT_EVENT = "AUDIT_EVENT"
    SUPERVISOR_EVENT = "SUPERVISOR_EVENT"
    METRIC_UPDATE = "METRIC_UPDATE"


class LatencyMetrics(BaseModel):
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    average_ms: float = 0.0
    sample_count: int = 0


class SystemOverview(BaseModel):
    system_status: ComponentStatus = ComponentStatus.HEALTHY
    production_mode: str = "PRODUCTION_SAFE"
    safety_state: SafetyState = SafetyState.NORMAL
    uptime_seconds: float = 0.0
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "2.0.0"
    environment: str = "production"
    active_streams_count: int = 0
    total_messages_processed: int = 0
    total_moderation_actions: int = 0
    total_cohost_responses: int = 0


class InfrastructureHealth(BaseModel):
    postgres_status: ComponentStatus = ComponentStatus.HEALTHY
    postgres_latency_ms: float = 0.0
    redis_status: ComponentStatus = ComponentStatus.HEALTHY
    redis_latency_ms: float = 0.0
    redis_fallback_active: bool = False
    event_bus_status: ComponentStatus = ComponentStatus.HEALTHY
    active_event_subscribers: int = 0
    websocket_status: ComponentStatus = ComponentStatus.HEALTHY
    active_websocket_connections: int = 0


class StreamOperations(BaseModel):
    stream_id: str
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    title: Optional[str] = None
    status: str = "OFFLINE"
    connection_status: str = "DISCONNECTED"
    viewers: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    moderation_actions: int = 0
    cohost_responses: int = 0
    reconnect_count: int = 0
    last_message_at: Optional[str] = None
    last_error: Optional[str] = None
    safety_state: SafetyState = SafetyState.NORMAL
    safe_mode: bool = False
    emergency_stop: bool = False
    cohost_enabled: bool = False
    moderation_enabled: bool = True
    dry_run: bool = True


class SafeCredentialSummary(BaseModel):
    key_alias: str = Field(description="Safe alias, e.g., 'KEY-1'")
    state: str = "AVAILABLE"
    total_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    cooldown_until: Optional[str] = None


class ProviderOperations(BaseModel):
    provider_name: str
    status: ComponentStatus = ComponentStatus.HEALTHY
    total_keys: int = 0
    healthy_keys: int = 0
    cooldown_keys: int = 0
    failed_keys: int = 0
    credentials: List[SafeCredentialSummary] = Field(default_factory=list)
    quota_failures: int = 0
    rate_limit_failures: int = 0
    total_requests: int = 0
    request_failures: int = 0


class AIHealth(BaseModel):
    provider_status: ComponentStatus = ComponentStatus.HEALTHY
    healthy_credentials: int = 0
    total_credentials: int = 0
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    quota_failures: int = 0
    fallback_count: int = 0
    queue_depth: int = 0
    moderation_requests: int = 0
    cohost_requests: int = 0
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)


class SystemHealthDetailed(BaseModel):
    overall_status: ComponentStatus = ComponentStatus.HEALTHY
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "2.0.0"
    environment: str = "production"
    uptime_seconds: float = 0.0
    infrastructure: InfrastructureHealth = Field(default_factory=InfrastructureHealth)
    youtube: ProviderOperations = Field(
        default_factory=lambda: ProviderOperations(provider_name="YouTube Data API v3")
    )
    gemini: AIHealth = Field(default_factory=AIHealth)
    supervisor_status: ComponentStatus = ComponentStatus.HEALTHY
    safety_controller: Dict[str, Any] = Field(default_factory=dict)
    streams: Dict[str, StreamOperations] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    audit_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor_id: str = "system"
    actor_role: str = "OPERATOR"
    action: str
    target: str = "system"
    stream_id: Optional[str] = None
    result: str = "SUCCESS"
    reason: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OperationalEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"opev_{uuid.uuid4().hex[:12]}")
    event_type: OperationalEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stream_id: Optional[str] = None
    actor_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
