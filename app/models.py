"""SQLAlchemy 2.x ORM models for Goddess AI 3.0."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(UTC)


class Channel(Base):
    """Registered YouTube channels."""

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), default="YouTube Channel", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ChannelSettings(Base):
    """Channel-scoped configuration for AI, Co-Host, Moderation, and Economy."""

    __tablename__ = "channel_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("channels.channel_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cohost_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    moderation_mode: Mapped[str] = mapped_column(
        String(32), default="balanced", nullable=False
    )  # relaxed/balanced/strict
    moderation_threshold: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    personality: Mapped[str] = mapped_column(String(64), default="friendly", nullable=False)
    xp_per_message: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    coins_per_message: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    reward_cooldown: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # seconds
    cohost_cooldown: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # seconds
    context_message_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base):
    """Channel-scoped viewer profile with XP, Level, and Coins."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    youtube_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), default="Viewer", nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reward_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("channel_id", "youtube_user_id", name="uq_user_channel_ytuser"),
        Index("ix_user_channel_ytuser", "channel_id", "youtube_user_id"),
    )


class Stream(Base):
    """YouTube Live Stream state for an active or past broadcast."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    live_chat_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="OFFLINE", nullable=False
    )  # OFFLINE, DETECTED, CONNECTING, LIVE, ENDING, ENDED, ERROR
    join_message_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("channel_id", "youtube_video_id", name="uq_stream_channel_video"),)


class ChatMessage(Base):
    """Persisted YouTube live chat messages for deduplication, context, and moderation."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stream_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="SET NULL"), index=True
    )
    youtube_message_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    youtube_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index(
            "ix_chat_messages_channel_stream_created",
            "channel_id",
            "stream_id",
            "created_at",
        ),
    )


class Command(Base):
    """Nightbot-style custom commands created by moderators/creator."""

    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # Normalized lowercase, e.g. "!discord"
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("channel_id", "name", name="uq_command_channel_name"),)


class StoreItem(Base):
    """Virtual store items available for purchase with coins."""

    __tablename__ = "store_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("channel_id", "item_name", name="uq_store_item_channel_name"),)


class Purchase(Base):
    """Historical purchase records with snapshot of cost paid."""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("store_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OneVOneQueueEntry(Base):
    """1v1 Matchmaking waiting list entries for active live stream."""

    __tablename__ = "one_v_one_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stream_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("streams.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    youtube_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="WAITING", nullable=False
    )  # WAITING, SELECTED, CANCELLED
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index(
            "ix_queue_channel_stream_status_joined",
            "channel_id",
            "stream_id",
            "status",
            "joined_at",
        ),
    )


class ModerationReview(Base):
    """Human-in-the-loop (HITL) moderation review queue for borderline messages."""

    __tablename__ = "moderation_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stream_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("streams.id", ondelete="SET NULL"), index=True
    )
    youtube_message_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_message: Mapped[str] = mapped_column(Text, nullable=False)
    model_category: Mapped[str] = mapped_column(String(64), nullable=False)
    model_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )  # PENDING, ALLOWED, BANNED, IGNORED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index(
            "ix_mod_reviews_channel_status_created",
            "channel_id",
            "status",
            "created_at",
        ),
    )


class ModerationMemory(Base):
    """Adaptive human-in-the-loop learning memory / RAG-lite context."""

    __tablename__ = "moderation_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    phrase: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="SAFE", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (Index("ix_mod_memory_channel_phrase", "channel_id", "phrase"),)


class WebSubSubscription(Base):
    """Tracks active WebSub/PubSubHubbub lease states for YouTube channels."""

    __tablename__ = "websub_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )  # PENDING, ACTIVE, EXPIRED, FAILED
    lease_expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_renewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Auditing trail for all privileged creator/moderator commands."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stream_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_username: Mapped[str] = mapped_column(String(128), nullable=False)
    command: Mapped[str] = mapped_column(String(64), nullable=False)
    safe_arguments: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result: Mapped[str] = mapped_column(String(64), nullable=False)  # SUCCESS, FAILED, DENIED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_audit_logs_channel_created", "channel_id", "created_at"),)
