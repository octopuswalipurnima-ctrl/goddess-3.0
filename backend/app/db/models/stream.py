"""
Persistent Stream and Stream Configuration Models for GODDESS AI 2.0.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StreamModel(Base, TimestampMixin):
    """Persistent representation of a YouTube stream session lifecycle."""
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    channel_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="INITIALIZING", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_streams_channel_status", "channel_id", "status"),
    )


class StreamConfigModel(Base, TimestampMixin):
    """Persistent stream-specific operational configuration."""
    __tablename__ = "stream_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
