"""
Data Models and Enums for Module System in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
from enum import Enum
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ModuleStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    LOADED = "LOADED"
    ENABLED = "ENABLED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    DISABLED = "DISABLED"
    FAILED = "FAILED"


class ModuleCapability(str, Enum):
    CHAT_READ = "CHAT_READ"
    CHAT_WRITE = "CHAT_WRITE"
    STREAM_READ = "STREAM_READ"
    MODERATION_READ = "MODERATION_READ"
    COHOST_READ = "COHOST_READ"
    AI_REQUEST = "AI_REQUEST"
    CONFIG_READ = "CONFIG_READ"
    CONFIG_WRITE = "CONFIG_WRITE"


class ModuleHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class ModuleMetadata(BaseModel):
    id: str = Field(..., description="Unique lowercase alphanumeric module identifier (e.g. 'commands', 'welcome')")
    name: str = Field(..., description="Human-readable module title")
    version: str = Field(default="1.0.0", description="SemVer module version string")
    description: str = Field(default="", description="Detailed description of module functionality")
    author: str = Field(default="Goddess AI Team", description="Module author or maintainer")
    category: str = Field(default="utility", description="Module category (e.g. 'interaction', 'utility', 'stats')")
    dependencies: List[str] = Field(default_factory=list, description="IDs of other modules required by this module")
    capabilities: List[ModuleCapability] = Field(default_factory=list, description="Declared capabilities/permissions")
    supported_events: List[str] = Field(default_factory=list, description="EventBus event names this module listens to")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", v_clean):
            raise ValueError("Module id must contain only lowercase alphanumeric characters, dashes, and underscores.")
        return v_clean


class ModuleHealth(BaseModel):
    status: ModuleHealthStatus = Field(default=ModuleHealthStatus.HEALTHY)
    details: str = Field(default="Module is operating normally")
    last_error: Optional[str] = Field(default=None)
    last_error_time: Optional[str] = Field(default=None)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ModuleInfo(BaseModel):
    metadata: ModuleMetadata
    status: ModuleStatus
    enabled: bool
    health: ModuleHealth
    load_time: Optional[str] = None
    active_streams: List[str] = Field(default_factory=list)


class StreamModuleConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether this module is active on the stream")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Module-specific per-stream configuration settings")
