"""
Data Models and Enums for AI Moderation Engine in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ModerationCategory(str, Enum):
    SAFE = "SAFE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    UNKNOWN = "UNKNOWN"
    SPAM = "SPAM"
    FLOOD = "FLOOD"
    REPEATED_MESSAGE = "REPEATED_MESSAGE"
    SCAM = "SCAM"
    MALICIOUS_LINK = "MALICIOUS_LINK"
    HARASSMENT = "HARASSMENT"
    INSULT = "INSULT"
    THREAT = "THREAT"
    HATEFUL_CONTENT = "HATEFUL_CONTENT"
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    SELF_HARM_RELATED = "SELF_HARM_RELATED"
    IMPERSONATION = "IMPERSONATION"
    OTHER = "OTHER"


class ModerationAction(str, Enum):
    NONE = "NONE"
    LOG = "LOG"
    WARN = "WARN"
    SLOW_MODE = "SLOW_MODE"
    DELETE = "DELETE"
    TIMEOUT = "TIMEOUT"
    BLOCK = "BLOCK"
    ESCALATE_TO_MODERATOR = "ESCALATE_TO_MODERATOR"


class ActionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserRole(str, Enum):
    OWNER = "OWNER"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"
    VIP = "VIP"
    USER = "USER"


class ModerationSource(str, Enum):
    RULE_ENGINE = "RULE_ENGINE"
    GEMINI_AI = "GEMINI_AI"
    MANUAL = "MANUAL"


class ActionStatus(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    EXECUTED = "EXECUTED"
    DRY_RUN = "DRY_RUN"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"
    FAILED = "FAILED"


class ModerationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    stream_id: str
    author_id: str
    author_name: str
    user_role: UserRole = Field(default=UserRole.USER)
    category: ModerationCategory = Field(default=ModerationCategory.SAFE)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    severity: ActionSeverity = Field(default=ActionSeverity.LOW)
    reason: str = Field(default="Message is safe")
    recommended_action: ModerationAction = Field(default=ModerationAction.NONE)
    source: ModerationSource = Field(default=ModerationSource.RULE_ENGINE)
    timestamp: float = Field(default_factory=time.time)


class ModerationAuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stream_id: str
    message_id: str
    author_id: str
    author_name: str
    decision: ModerationDecision
    action_taken: ModerationAction = Field(default=ModerationAction.NONE)
    action_status: ActionStatus = Field(default=ActionStatus.APPROVED)
    block_reason: Optional[str] = Field(default=None)
    idempotency_key: str


class StreamModerationConfig(BaseModel):
    enabled: bool = Field(default=True, description="Master enable toggle for moderation on this stream")
    automation_enabled: bool = Field(default=True, description="Enable automated action execution")
    dry_run: bool = Field(default=False, description="Dry-run mode: evaluate decisions but do not execute on YouTube")
    safe_mode: bool = Field(default=False, description="Restrict automated actions to highest-confidence rule actions only")
    kill_switch: bool = Field(default=False, description="Emergency stop all automated actions immediately")
    circuit_breaker_tripped: bool = Field(default=False, description="Circuit breaker state when action storm is detected")
    circuit_breaker_action_threshold: int = Field(default=10, ge=3, description="Max actions allowed within short window before tripping circuit breaker")
    circuit_breaker_window_seconds: float = Field(default=10.0, ge=1.0, description="Sliding window duration for circuit breaker")
    ai_enabled: bool = Field(default=True, description="Enable Gemini AI contextual moderation")
    ai_confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0, description="Minimum AI confidence for actions")
    spam_enabled: bool = Field(default=True)
    flood_enabled: bool = Field(default=True)
    link_detection_enabled: bool = Field(default=True)
    repeat_detection_enabled: bool = Field(default=True)
    owner_exempt: bool = Field(default=True)
    moderator_exempt: bool = Field(default=True)
    member_exempt: bool = Field(default=False)
    cooldown_seconds_per_user: int = Field(default=10, ge=0, description="Cooldown between automated actions on same user")
    max_actions_per_minute: int = Field(default=30, ge=1, description="Max actions allowed per minute per stream")


class ModerationMetrics(BaseModel):
    messages_analyzed: int = 0
    rule_matches: int = 0
    ai_classifications: int = 0
    actions_approved: int = 0
    actions_blocked: int = 0
    actions_executed: int = 0
    actions_dry_run: int = 0
    actions_failed: int = 0
    ai_failures: int = 0
    circuit_breaker_trips: int = 0
