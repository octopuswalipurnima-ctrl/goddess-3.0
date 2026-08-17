"""
Persistent Module Configuration Model for GODDESS AI 2.0.
"""

from typing import Any, Dict
from sqlalchemy import Boolean, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ModuleConfigModel(Base, TimestampMixin):
    """Persistent stream-specific module configurations."""
    __tablename__ = "module_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stream_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("module_id", "stream_id", name="uq_module_stream_config"),
        Index("ix_module_configs_stream", "stream_id", "module_id"),
    )
