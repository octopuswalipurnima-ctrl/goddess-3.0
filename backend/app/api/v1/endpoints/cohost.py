"""
REST API Endpoints for AI Co-Host Engine in GODDESS AI 2.0.

Provides endpoints to manage per-stream Co-Host configs, persona attributes,
emergency controls, audit history, and dry-run test simulations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.cohost import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostMetrics,
    CoHostPersonality,
    CoHostResponse,
    cohost_audit_logger,
    cohost_manager,
)
from app.services.youtube.models import ChatMessage

router = APIRouter(prefix="/cohost", tags=["Co-Host Engine"])


class CoHostConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    dry_run: Optional[bool] = None
    emergency_stop: Optional[bool] = None
    personality_enabled: Optional[bool] = None
    ai_enabled: Optional[bool] = None
    respond_to_mentions: Optional[bool] = None
    respond_to_questions: Optional[bool] = None
    respond_to_relevant_messages: Optional[bool] = None
    global_response_cooldown: Optional[float] = Field(default=None, ge=0.0)
    per_user_response_cooldown: Optional[float] = Field(default=None, ge=0.0)
    max_responses_per_minute: Optional[int] = Field(default=None, ge=1)
    max_responses_per_user: Optional[int] = Field(default=None, ge=1)
    context_window_size: Optional[int] = Field(default=None, ge=1, le=100)
    user_context_window_size: Optional[int] = Field(default=None, ge=1, le=20)
    minimum_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_response_length: Optional[int] = Field(default=None, ge=10, le=500)
    language: Optional[str] = None
    personality: Optional[CoHostPersonality] = None


class CoHostTestRequest(BaseModel):
    stream_id: str = Field(default="test_stream", description="Target stream ID")
    author_id: str = Field(default="test_viewer_1", description="Author user ID")
    author_name: str = Field(default="TestViewer", description="Author display name")
    message_text: str = Field(..., min_length=1, max_length=500, description="Chat text to simulate")
    is_chat_owner: bool = False
    is_chat_moderator: bool = False
    is_chat_sponsor: bool = False


@router.get("/config/{stream_id}", response_model=CoHostConfig, summary="Get Stream Co-Host Configuration")
async def get_stream_config(stream_id: str):
    """Retrieve Co-Host settings and persona for a specific stream."""
    return cohost_manager.get_config(stream_id)


@router.put("/config/{stream_id}", response_model=CoHostConfig, summary="Update Stream Co-Host Configuration")
async def update_stream_config(stream_id: str, payload: CoHostConfigUpdateRequest):
    """Update Co-Host settings (e.g. toggle enabled, dry-run, emergency stop, personality)."""
    updates = payload.model_dump(exclude_unset=True)
    return cohost_manager.update_config(stream_id, updates)


@router.get("/audit/{stream_id}", response_model=List[CoHostAuditRecord], summary="Get Recent Co-Host Audit Log")
async def get_stream_audit_log(stream_id: str, limit: int = 50):
    """Fetch the latest Co-Host generated replies and audit records for a stream."""
    return cohost_audit_logger.get_recent_records(stream_id, limit=limit)


@router.get("/stats", response_model=CoHostMetrics, summary="Get Co-Host Metrics")
async def get_cohost_stats():
    """Fetch global Co-Host metrics (messages analyzed, intents, responses sent, dry-run, blocked)."""
    return cohost_manager.metrics


@router.post("/test", response_model=Optional[CoHostResponse], summary="Dry-Run Test Co-Host Response")
async def test_cohost(payload: CoHostTestRequest):
    """
    Simulate processing a chat message through the Co-Host pipeline in DRY_RUN mode.
    """
    dummy_msg = ChatMessage(
        message_id=f"test_cohost_{int(payload.message_text.__hash__() % 1000000)}",
        stream_id=payload.stream_id,
        author_id=payload.author_id,
        author_name=payload.author_name,
        message_text=payload.message_text,
        is_chat_owner=payload.is_chat_owner,
        is_chat_moderator=payload.is_chat_moderator,
        is_chat_sponsor=payload.is_chat_sponsor,
    )

    # Ensure config has enabled=True, dry_run=True for test simulation
    cfg = cohost_manager.get_config(payload.stream_id)
    orig_enabled = cfg.enabled
    orig_dry_run = cfg.dry_run
    try:
        cohost_manager.update_config(payload.stream_id, {"enabled": True, "dry_run": True})
        return await cohost_manager.process_message(dummy_msg)
    finally:
        cohost_manager.update_config(payload.stream_id, {"enabled": orig_enabled, "dry_run": orig_dry_run})
