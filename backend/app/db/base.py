"""
SQLAlchemy 2.0 Base Models and Mixins for GODDESS AI 2.0.

Provides standard DeclarativeBase, UTC timestamp mixins, and common model utilities.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Helper to return naive or timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative Base class for all persistent SQLAlchemy models."""
    pass


class TimestampMixin:
    """Standard audit mixin providing created_at and updated_at UTC timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
