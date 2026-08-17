"""
REST API Endpoints for AI Co-Host Engine in GODDESS AI 2.0.
Provides stream-scoped endpoints for Co-Host configuration, personality,
creator knowledge base, stream awareness, audit records, and dry-run simulations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.services.cohost import (
    CoHostAuditRecord,
    CoHostConfig,
    CoHostMetrics,
    CoHostPersonality,
    CoHostResponse,
    CreatorKnowledge,
    StreamAwarenessData,
    cohost_audit_logger,
    cohost_manager,
    cohost_personality_manager,
    creator_knowledge_manager,
    stream_awareness_engine,
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
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    response_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_regeneration_attempts: Optional[int] = Field(default=None, ge=0, le=3)
    max_response_length: Optional[int] = Field(default=None, ge=10, le=500)
    language: Optional[str] = None
    personality: Optional[CoHostPersonality] = None


class PersonalityUpdateRequest(BaseModel):
    name: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    energy_level: Optional[str] = None
    humor_level: Optional[str] = None
    friendliness: Optional[str] = None
    formality: Optional[str] = None
    emoji_usage: Optional[str] = None
    response_style: Optional[str] = None
    language: Optional[str] = None
    custom_instructions: Optional[str] = None
    enabled: Optional[bool] = None


class KnowledgeCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=1000)
    category: str = Field(default="general")
    enabled: bool = True


class AwarenessUpdateRequest(BaseModel):
    current_activity: Optional[str] = None
    category: Optional[str] = None
    stream_status: Optional[str] = None
    custom_facts: Optional[Dict[str, str]] = None


class CoHostTestRequest(BaseModel):
    stream_id: str = Field(default="test_stream", description="Target stream ID")
    author_id: str = Field(default="test_viewer_1", description="Author user ID")
    author_name: str = Field(default="TestViewer", description="Author display name")
    message_text: str = Field(..., min_length=1, max_length=500, description="Chat text to simulate")
    is_chat_owner: bool = False
    is_chat_moderator: bool = False
    is_chat_sponsor: bool = False


# --- Configuration Endpoints ---

@router.get(
    "/config/{stream_id}",
    response_model=CoHostConfig,
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Stream Co-Host Configuration",
)
async def get_stream_config(stream_id: str):
    """Retrieve Co-Host settings and persona for a specific stream."""
    return cohost_manager.get_config(stream_id)


@router.put(
    "/config/{stream_id}",
    response_model=CoHostConfig,
    dependencies=[Depends(require_permission("cohost.configure"))],
    summary="Update Stream Co-Host Configuration",
)
async def update_stream_config(stream_id: str, payload: CoHostConfigUpdateRequest):
    """Update Co-Host settings (e.g. toggle enabled, dry-run, emergency stop, personality)."""
    updates = payload.model_dump(exclude_unset=True)
    return cohost_manager.update_config(stream_id, updates)


# --- Personality Endpoints ---

@router.get(
    "/personality/{stream_id}",
    response_model=CoHostPersonality,
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Stream Personality",
)
async def get_stream_personality(stream_id: str):
    """Retrieve stream-specific Co-Host persona configuration."""
    return cohost_personality_manager.get_personality(stream_id)


@router.put(
    "/personality/{stream_id}",
    response_model=CoHostPersonality,
    dependencies=[Depends(require_permission("cohost.configure"))],
    summary="Update Stream Personality",
)
async def update_stream_personality(stream_id: str, payload: PersonalityUpdateRequest):
    """Update stream-specific Co-Host persona (tone, energy, humor, style, custom instructions)."""
    updates = payload.model_dump(exclude_unset=True)
    return cohost_personality_manager.update_personality(stream_id, updates)


# --- Knowledge Base Endpoints ---

@router.get(
    "/knowledge/{stream_id}",
    response_model=List[CreatorKnowledge],
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Stream Knowledge Base",
)
async def get_stream_knowledge(stream_id: str):
    """Fetch all creator-approved facts for a stream."""
    return creator_knowledge_manager.get_knowledge_entries(stream_id)


@router.post(
    "/knowledge/{stream_id}",
    response_model=CreatorKnowledge,
    dependencies=[Depends(require_permission("cohost.configure"))],
    summary="Add / Update Knowledge Fact",
)
async def set_stream_knowledge_fact(stream_id: str, payload: KnowledgeCreateRequest):
    """Add or update a verified creator fact for a stream."""
    return creator_knowledge_manager.set_fact(
        stream_id=stream_id,
        key=payload.key,
        value=payload.value,
        category=payload.category,
        enabled=payload.enabled,
    )


@router.delete(
    "/knowledge/{stream_id}/{key}",
    dependencies=[Depends(require_permission("cohost.configure"))],
    summary="Delete Knowledge Fact",
)
async def delete_stream_knowledge_fact(stream_id: str, key: str):
    """Delete a creator fact from stream knowledge base."""
    deleted = creator_knowledge_manager.delete_fact(stream_id, key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fact '{key}' not found.")
    return {"status": "success", "message": f"Fact '{key}' deleted."}


# --- Stream Awareness Endpoints ---

@router.get(
    "/awareness/{stream_id}",
    response_model=StreamAwarenessData,
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Stream Awareness State",
)
async def get_stream_awareness(stream_id: str):
    """Retrieve stream awareness metadata (current activity, status, custom facts)."""
    return stream_awareness_engine.get_awareness(stream_id)


@router.put(
    "/awareness/{stream_id}",
    response_model=StreamAwarenessData,
    dependencies=[Depends(require_permission("cohost.configure"))],
    summary="Update Stream Awareness",
)
async def update_stream_awareness(stream_id: str, payload: AwarenessUpdateRequest):
    """Update stream awareness state (e.g. game being played, custom facts)."""
    updates = payload.model_dump(exclude_unset=True)
    return stream_awareness_engine.update_awareness(stream_id, updates)


# --- Audit & Telemetry Endpoints ---

@router.get(
    "/audit/{stream_id}",
    response_model=List[CoHostAuditRecord],
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Recent Co-Host Audit Log",
)
async def get_stream_audit_log(stream_id: str, limit: int = 50):
    """Fetch the latest Co-Host generated replies and audit records for a stream."""
    return cohost_audit_logger.get_recent_records(stream_id, limit=limit)


@router.get(
    "/stats",
    response_model=CoHostMetrics,
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Get Co-Host Metrics",
)
async def get_cohost_stats():
    """Fetch global Co-Host metrics (messages analyzed, intents, engagement decisions, dry-run, blocked)."""
    return cohost_manager.metrics


@router.post(
    "/test",
    response_model=Optional[CoHostResponse],
    dependencies=[Depends(require_permission("cohost.read"))],
    summary="Dry-Run Test Co-Host Response",
)
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
