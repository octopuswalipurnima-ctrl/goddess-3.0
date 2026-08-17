"""
Persistent Co-Host Configuration and Audit Record Models for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utc_now


class CoHostConfigModel(Base, TimestampMixin):
    """Persistent stream-specific Co-Host configuration and personality settings."""
    __tablename__ = "cohost_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    personality_name: Mapped[str] = mapped_column(String(64), default="goddess", nullable=False)
    cooldown_seconds: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CoHostAuditRecordModel(Base, TimestampMixin):
    """Persistent audit log of generated Co-Host responses and intent detections."""
    __tablename__ = "cohost_audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False)
    intent: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_text: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="SENT", nullable=False)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_cohost_audit_stream_time", "stream_id", "timestamp"),
    )
