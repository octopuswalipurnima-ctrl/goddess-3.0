"""
REST API Endpoints for AI Moderation Engine in GODDESS AI 2.0.

Provides endpoints to manage per-stream moderation configs, emergency controls
(kill switch, safe mode, dry-run, circuit breaker reset), retrieve audit records, and run test evaluations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.moderation import (
    ModerationAuditRecord,
    ModerationDecision,
    ModerationMetrics,
    StreamModerationConfig,
    moderation_audit_logger,
    moderation_manager,
)
from app.services.youtube.models import ChatMessage

router = APIRouter(prefix="/moderation", tags=["Moderation Engine"])


class ModerationConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    automation_enabled: Optional[bool] = None
    dry_run: Optional[bool] = None
    safe_mode: Optional[bool] = None
    kill_switch: Optional[bool] = None
    circuit_breaker_tripped: Optional[bool] = None
    circuit_breaker_action_threshold: Optional[int] = Field(default=None, ge=3)
    circuit_breaker_window_seconds: Optional[float] = Field(default=None, ge=1.0)
    ai_enabled: Optional[bool] = None
    ai_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    spam_enabled: Optional[bool] = None
    flood_enabled: Optional[bool] = None
    link_detection_enabled: Optional[bool] = None
    repeat_detection_enabled: Optional[bool] = None
    owner_exempt: Optional[bool] = None
    moderator_exempt: Optional[bool] = None
    member_exempt: Optional[bool] = None
    cooldown_seconds_per_user: Optional[int] = Field(default=None, ge=0)


class ModerationTestRequest(BaseModel):
    stream_id: str = Field(default="test_stream", description="Stream ID context")
    author_id: str = Field(default="test_user_1", description="Author user ID")
    author_name: str = Field(default="TestViewer", description="Author display name")
    message_text: str = Field(..., min_length=1, max_length=500, description="Chat text to analyze")
    is_chat_owner: bool = False
    is_chat_moderator: bool = False
    is_chat_sponsor: bool = False


@router.get("/config/{stream_id}", response_model=StreamModerationConfig, summary="Get Stream Moderation Configuration")
async def get_stream_config(stream_id: str):
    """Retrieve moderation settings for a specific stream."""
    return moderation_manager.get_config(stream_id)


@router.put("/config/{stream_id}", response_model=StreamModerationConfig, summary="Update Stream Moderation Configuration")
async def update_stream_config(stream_id: str, payload: ModerationConfigUpdateRequest):
    """Update moderation settings (e.g. toggle emergency kill switch, safe mode, dry-run, automation)."""
    updates = payload.model_dump(exclude_unset=True)
    return moderation_manager.update_config(stream_id, updates)


@router.post("/circuit-breaker/reset/{stream_id}", response_model=StreamModerationConfig, summary="Reset Moderation Circuit Breaker")
async def reset_circuit_breaker(stream_id: str):
    """Explicitly reset the automatic moderation circuit breaker for a stream."""
    return moderation_manager.reset_circuit_breaker(stream_id)


@router.get("/audit/{stream_id}", response_model=List[ModerationAuditRecord], summary="Get Recent Moderation Audit Log")
async def get_stream_audit_log(stream_id: str, limit: int = 50):
    """Fetch the latest moderation decisions and action audit records for a stream."""
    return moderation_audit_logger.get_recent_records(stream_id, limit=limit)


@router.get("/stats", response_model=ModerationMetrics, summary="Get Moderation Metrics")
async def get_moderation_stats():
    """Fetch global moderation metrics (messages analyzed, rule matches, actions executed/blocked, dry-runs)."""
    return moderation_manager.metrics


@router.post("/test", response_model=ModerationDecision, summary="Dry-Run Test Chat Message Moderation")
async def test_moderation(payload: ModerationTestRequest):
    """
    Dry-run evaluate a test message through the 3-tier moderation engine
    without executing destructive actions on YouTube.
    """
    dummy_msg = ChatMessage(
        message_id=f"test_msg_{int(payload.message_text.__hash__() % 1000000)}",
        stream_id=payload.stream_id,
        author_id=payload.author_id,
        author_name=payload.author_name,
        message_text=payload.message_text,
        is_chat_owner=payload.is_chat_owner,
        is_chat_moderator=payload.is_chat_moderator,
        is_chat_sponsor=payload.is_chat_sponsor,
    )

    return await moderation_manager.process_message(dummy_msg)
