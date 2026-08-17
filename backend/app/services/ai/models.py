"""
AI Models and Data Structures for GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIActionType(str, Enum):
    NONE = "NONE"
    MODERATE_DELETE = "MODERATE_DELETE"
    MODERATE_TIMEOUT = "MODERATE_TIMEOUT"
    MODERATE_BAN = "MODERATE_BAN"
    MODERATE_LOG = "MODERATE_LOG"
    COHOST_REPLY = "COHOST_REPLY"
    COHOST_DRY_RUN = "COHOST_DRY_RUN"
    COMMAND_REPLY = "COMMAND_REPLY"
    SAFE_PASS = "SAFE_PASS"
    FAIL_CLOSED = "FAIL_CLOSED"


class AIConfig(BaseModel):
    """Per-stream AI Intelligence Configuration."""
    stream_id: str
    enabled: bool = True
    dry_run: bool = False
    cooldown_seconds: float = Field(default=5.0, ge=0.0)
    max_response_length: int = Field(default=200, ge=1, le=200)
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    response_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    allowed_intents: List[str] = Field(
        default_factory=lambda: [
            "QUESTION", "GREETING", "GAME_QUERY", "SHOUTOUT", "STREAM_TOPIC", "GENERAL_CHAT"
        ]
    )
    daily_token_budget: int = Field(default=500_000, ge=1)
    daily_request_budget: int = Field(default=10_000, ge=1)


class AIDecision(BaseModel):
    """Structured, auditable AI Decision Result."""
    decision_id: str
    stream_id: str
    message_id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    action: AIActionType = AIActionType.NONE
    confidence: float = 0.0
    category: str = "general"
    reason: str = "Evaluated by AI Decision Engine"
    priority: str = "NORMAL"
    should_reply: bool = False
    should_moderate: bool = False
    reply_text: Optional[str] = None
    model_used: Optional[str] = None
    fallback_used: bool = False
    latency_ms: Optional[float] = None
    tokens_used: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
