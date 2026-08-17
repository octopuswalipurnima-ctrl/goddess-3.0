"""
Data Models and Enums for AI Co-Host Engine in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    IGNORE = "IGNORE"
    GREETING = "GREETING"
    QUESTION = "QUESTION"
    STREAM_TOPIC = "STREAM_TOPIC"
    GAMEPLAY = "GAMEPLAY"
    JOIN_REQUEST = "JOIN_REQUEST"
    COMMAND_REQUEST = "COMMAND_REQUEST"
    COMPLIMENT = "COMPLIMENT"
    THANKS = "THANKS"
    REACTION = "REACTION"
    CONVERSATION = "CONVERSATION"
    MENTION = "MENTION"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


class ResponseStatus(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    SENT = "SENT"
    DRY_RUN = "DRY_RUN"
    FAILED = "FAILED"


class CoHostPersonality(BaseModel):
    name: str = Field(default="Goddess", description="Persona display name")
    tone: str = Field(default="friendly", description="Emotional tone (friendly, witty, enthusiastic)")
    style: str = Field(default="energetic", description="Conversational style")
    humor_level: str = Field(default="moderate", description="Humor level (subtle, moderate, high)")
    formality: str = Field(default="casual", description="Formality level (casual, polite, formal)")
    energy: str = Field(default="high", description="Energy level (chill, high, hyped)")
    language: str = Field(default="auto", description="Preferred reply language")
    custom_instructions: str = Field(default="", description="Creator-provided custom personality instructions")


class CoHostIntent(BaseModel):
    intent_type: IntentType = Field(default=IntentType.UNKNOWN)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(default="Default intent determination")
    source: str = Field(default="RULE_ENGINE", description="RULE_ENGINE or GEMINI_AI")


class CoHostMessage(BaseModel):
    stream_id: str
    channel_id: str = "default_channel"
    message_id: str
    author_id: str
    author_name: str
    message_text: str
    timestamp: float = Field(default_factory=time.time)
    user_role: str = "USER"
    is_mention: bool = False
    is_question: bool = False
    urls: List[str] = Field(default_factory=list)


class CoHostResponse(BaseModel):
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str
    message_id: str
    author_id: str
    author_name: str
    response_text: str
    status: ResponseStatus = Field(default=ResponseStatus.APPROVED)
    intent: CoHostIntent = Field(default_factory=CoHostIntent)
    latency_ms: float = Field(default=0.0)
    model: str = Field(default="gemini-2.5-flash")
    block_reason: Optional[str] = Field(default=None)
    timestamp: float = Field(default_factory=time.time)


class CoHostConfig(BaseModel):
    enabled: bool = Field(default=False, description="Opt-in master enable toggle for Co-Host on this stream")
    dry_run: bool = Field(default=True, description="Dry-run mode: generate responses but do not send to YouTube chat")
    emergency_stop: bool = Field(default=False, description="Emergency stop all public Co-Host responses immediately")
    personality_enabled: bool = Field(default=True, description="Enable custom personality framing")
    ai_enabled: bool = Field(default=True, description="Enable Gemini AI contextual response generation")
    respond_to_mentions: bool = Field(default=True, description="Respond when viewers directly mention the bot")
    respond_to_questions: bool = Field(default=True, description="Respond to stream and game questions")
    respond_to_relevant_messages: bool = Field(default=True, description="Respond to conversational prompts")
    global_response_cooldown: float = Field(default=5.0, ge=0.0, description="Minimum seconds between any public responses")
    per_user_response_cooldown: float = Field(default=30.0, ge=0.0, description="Minimum seconds between replies to the same viewer")
    max_responses_per_minute: int = Field(default=12, ge=1, description="Max responses allowed per minute per stream")
    max_responses_per_user: int = Field(default=3, ge=1, description="Max responses allowed per user in sliding window")
    context_window_size: int = Field(default=20, ge=1, le=100, description="Max stream chat messages retained in short-term context")
    user_context_window_size: int = Field(default=5, ge=1, le=20, description="Max per-user interactions retained in short-term context")
    minimum_confidence: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum intent confidence to trigger response")
    max_response_length: int = Field(default=200, ge=10, le=500, description="Maximum character length of generated response")
    language: str = Field(default="auto")
    personality: CoHostPersonality = Field(default_factory=CoHostPersonality)


class CoHostAuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stream_id: str
    message_id: str
    author_id: str
    author_name: str
    user_message: str
    intent: IntentType
    intent_confidence: float
    response_text: Optional[str] = None
    response_status: ResponseStatus
    dry_run: bool
    response_length: int = 0
    latency_ms: float = 0.0
    model: str = "gemini-2.5-flash"
    block_reason: Optional[str] = None


class CoHostMetrics(BaseModel):
    messages_analyzed: int = 0
    intents_detected: int = 0
    responses_requested: int = 0
    responses_generated: int = 0
    responses_sent: int = 0
    responses_dry_run: int = 0
    responses_blocked: int = 0
    responses_failed: int = 0
    ai_timeouts: int = 0
