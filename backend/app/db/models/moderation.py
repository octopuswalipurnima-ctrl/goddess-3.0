"""
Persistent Moderation Audit Record Model for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utc_now


class ModerationAuditRecordModel(Base, TimestampMixin):
    """Persistent audit log of all 3-tier moderation decisions and actions taken."""
    __tablename__ = "moderation_audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(64), default="NONE", nullable=False)
    action_taken: Mapped[str] = mapped_column(String(64), default="NONE", nullable=False)
    action_status: Mapped[str] = mapped_column(String(32), index=True, default="APPROVED", nullable=False)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_mod_audit_stream_time", "stream_id", "timestamp"),
        Index("ix_mod_audit_stream_category", "stream_id", "category"),
        UniqueConstraint("stream_id", "message_id", "action_taken", name="uq_mod_audit_stream_msg_action"),
    )
