"""
Data Models and Enums for YouTube Engine in GODDESS AI 2.0.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CredentialState(str, Enum):
    UNCONFIGURED = "UNCONFIGURED"
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    COOLDOWN = "COOLDOWN"
    DISABLED = "DISABLED"


class CredentialHealth(BaseModel):
    key_id: str = Field(description="Safe key identifier, e.g., 'youtube-key-1'")
    state: CredentialState = Field(default=CredentialState.AVAILABLE)
    failure_count: int = Field(default=0)
    total_requests: int = Field(default=0)
    last_used: Optional[str] = Field(default=None)
    cooldown_until: Optional[str] = Field(default=None)
    last_error: Optional[str] = Field(default=None)


class StreamStatus(str, Enum):
    STANDBY = "STANDBY"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    ENDED = "ENDED"
    FAILED = "FAILED"


class LiveStreamInfo(BaseModel):
    stream_id: str
    channel_id: str
    title: str
    status: StreamStatus = Field(default=StreamStatus.STANDBY)
    concurrent_viewers: int = Field(default=0)
    live_chat_id: Optional[str] = None
    scheduled_start_time: Optional[str] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ChatMessage(BaseModel):
    message_id: str
    stream_id: str
    channel_id: str
    author_id: str
    author_name: str
    author_avatar_url: Optional[str] = None
    message_text: str
    published_at: str
    is_chat_owner: bool = False
    is_chat_moderator: bool = False
    is_chat_sponsor: bool = False  # Channel Member
    is_super_chat: bool = False
    super_chat_amount: Optional[str] = None


class SessionMetrics(BaseModel):
    messages_received: int = 0
    messages_published: int = 0
    polling_errors: int = 0
    reconnect_count: int = 0
    start_time: Optional[float] = None
    last_activity_time: Optional[float] = None


class StreamSessionSummary(BaseModel):
    stream_id: str
    channel_id: Optional[str] = None
    title: Optional[str] = None
    status: StreamStatus
    live_chat_id: Optional[str] = None
    concurrent_viewers: int = 0
    messages_received: int = 0
    reconnect_count: int = 0
    uptime_seconds: float = 0.0
    last_activity: Optional[str] = None
