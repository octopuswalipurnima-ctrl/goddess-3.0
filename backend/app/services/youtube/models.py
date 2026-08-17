"""
Data Models and Enums for YouTube Engine in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
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
    credential_id: Optional[str] = Field(default=None, description="Alias for key_id")
    state: CredentialState = Field(default=CredentialState.AVAILABLE)
    failure_count: int = Field(default=0)
    consecutive_failures: int = Field(default=0)
    total_requests: int = Field(default=0)
    successful_requests: int = Field(default=0)
    failed_requests: int = Field(default=0)
    quota_failures: int = Field(default=0)
    rate_limit_failures: int = Field(default=0)
    last_used: Optional[str] = Field(default=None)
    last_used_at: Optional[str] = Field(default=None)
    cooldown_until: Optional[str] = Field(default=None)
    last_error: Optional[str] = Field(default=None)
    last_error_type: Optional[str] = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        if self.credential_id is None:
            self.credential_id = self.key_id
        if self.last_used_at is None and self.last_used is not None:
            self.last_used_at = self.last_used


class StreamStatus(str, Enum):
    STANDBY = "STANDBY"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    RECONNECTING = "RECONNECTING"
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
    channel_id: str = Field(default="default_channel")
    author_id: str
    author_name: str
    author_avatar_url: Optional[str] = None
    message_text: str
    published_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_chat_owner: bool = False
    is_chat_moderator: bool = False
    is_chat_sponsor: bool = False  # Channel Member
    is_super_chat: bool = False
    super_chat_amount: Optional[str] = None


class ChatMessageEvent(BaseModel):
    """Normalized safe chat event for EventBus and internal processing."""
    event_id: str
    stream_id: str
    message_id: str
    author_id: str
    author_display_name: str
    message_text: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionMetrics(BaseModel):
    messages_received: int = 0
    messages_published: int = 0
    messages_sent: int = 0
    polling_errors: int = 0
    reconnect_count: int = 0
    start_time: Optional[float] = None
    connected_at: Optional[float] = None
    last_activity_time: Optional[float] = None
    last_message_at: Optional[float] = None
    last_reconnect_at: Optional[float] = None


class StreamSessionSummary(BaseModel):
    stream_id: str
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    title: Optional[str] = None
    status: StreamStatus
    connection_status: Optional[str] = None
    live_chat_id: Optional[str] = None
    concurrent_viewers: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    reconnect_count: int = 0
    uptime_seconds: float = 0.0
    connected_at: Optional[str] = None
    last_activity: Optional[str] = None
    last_message_at: Optional[str] = None
    last_reconnect_at: Optional[str] = None
    current_credential_id: Optional[str] = None
    provider_health: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.video_id is None:
            self.video_id = self.stream_id
        if self.connection_status is None:
            self.connection_status = self.status.value
