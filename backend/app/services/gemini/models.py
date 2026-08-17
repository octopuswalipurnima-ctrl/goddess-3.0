"""
Data Models and Enums for Gemini AI Engine in GODDESS AI 2.0.
"""

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Dict, Optional
import uuid
import time
from pydantic import BaseModel, Field


class AIRequestPriority(IntEnum):
    HIGH = 1      # Moderation, critical stream safety
    NORMAL = 2    # Viewer interaction, direct co-host replies
    LOW = 3       # Background analytics, summary tasks


class AIResponseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_ERROR = "AUTH_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    MODEL_ERROR = "MODEL_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class CredentialState(str, Enum):
    UNCONFIGURED = "UNCONFIGURED"
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    COOLDOWN = "COOLDOWN"
    DISABLED = "DISABLED"


class CredentialHealth(BaseModel):
    key_id: str = Field(description="Safe key identifier, e.g., 'gemini-key-1'")
    state: CredentialState = Field(default=CredentialState.AVAILABLE)
    failure_count: int = Field(default=0)
    total_requests: int = Field(default=0)
    last_used: Optional[str] = Field(default=None)
    cooldown_until: Optional[str] = Field(default=None)
    last_error: Optional[str] = Field(default=None)


class AIRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str = Field(..., description="Target stream ID for multi-stream isolation")
    channel_id: Optional[str] = Field(default=None, description="Associated YouTube Channel ID")
    source: str = Field(default="generic", description="Originating subsystem (e.g. moderation, cohost, test)")
    prompt: str = Field(..., min_length=1, description="Input prompt text for Gemini")
    system_instruction: Optional[str] = Field(default=None, description="Optional system instruction / persona")
    model_preference: Optional[str] = Field(default=None, description="Optional explicit model name override")
    priority: AIRequestPriority = Field(default=AIRequestPriority.NORMAL, description="Scheduling priority (HIGH/NORMAL/LOW)")
    timeout_seconds: Optional[float] = Field(default=None, description="Optional custom timeout override")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, gt=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class AIResponse(BaseModel):
    request_id: str
    stream_id: str
    status: AIResponseStatus = Field(default=AIResponseStatus.SUCCESS)
    text: str = Field(default="", description="Generated response content (non-empty on SUCCESS)")
    model: str = Field(default="", description="Actual Gemini model used for generation")
    credential_id: Optional[str] = Field(default=None, description="Safe credential identifier (e.g. 'gemini-key-1')")
    finish_reason: Optional[str] = Field(default=None, description="Gemini finishReason (e.g. STOP, MAX_TOKENS, SAFETY)")
    latency_seconds: float = Field(default=0.0, description="Total round-trip latency in seconds")
    token_usage: Optional[Dict[str, int]] = Field(default=None, description="Input/Output token counts if available")
    error_message: Optional[str] = Field(default=None, description="Error diagnostics on non-SUCCESS status")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeminiMetrics(BaseModel):
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    empty_responses: int = 0
    timeouts: int = 0
    rate_limited_count: int = 0
    retries_count: int = 0
    model_fallbacks_count: int = 0
    active_requests: int = 0
    queued_requests: int = 0
    total_latency_seconds: float = 0.0

    @property
    def average_latency_seconds(self) -> float:
        if self.successful_requests > 0:
            return round(self.total_latency_seconds / self.successful_requests, 3)
        return 0.0
