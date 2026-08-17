"""
Persistent Creator Settings Model for GODDESS AI 2.0.
"""

from typing import Any, Dict
from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class CreatorSettingsModel(Base, TimestampMixin):
    """Persistent key-value creator preferences and platform defaults."""
    __tablename__ = "creator_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
