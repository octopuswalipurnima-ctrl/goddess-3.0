"""
Development & Diagnostic AI Endpoints for GODDESS AI 2.0.

Provides controlled test endpoints to submit prompts to the Gemini AI Engine
and observe rate limiting, model routing, and normalized response structures.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.gemini import (
    AIRequest,
    AIRequestPriority,
    AIResponse,
    AIResponseStatus,
    gemini_manager,
)

router = APIRouter(prefix="/ai", tags=["AI Engine"])


class AITestRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Test prompt text")
    stream_id: str = Field(default="test_stream", description="Stream ID for multi-stream routing context")
    system_instruction: Optional[str] = Field(default=None, description="Optional system persona/instruction")
    model_preference: Optional[str] = Field(default=None, description="Optional model override (e.g. gemini-2.5-flash)")
    priority: int = Field(default=2, ge=1, le=3, description="Priority (1=HIGH, 2=NORMAL, 3=LOW)")


@router.post("/test", response_model=AIResponse, summary="Development Gemini AI Generation Test Endpoint")
async def test_ai_generation(payload: AITestRequest):
    """
    Submits a test prompt to the Gemini AI Engine.
    Executes through priority queue, token-bucket rate limiter, credential manager, and model router.
    """
    request_priority = AIRequestPriority(payload.priority)

    req = AIRequest(
        stream_id=payload.stream_id,
        source="api_test_endpoint",
        prompt=payload.prompt,
        system_instruction=payload.system_instruction,
        model_preference=payload.model_preference,
        priority=request_priority,
    )

    response = await gemini_manager.request(req)

    if response.status == AIResponseStatus.AUTH_ERROR:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=response.error_message or "Gemini API credentials not configured or unauthorized.",
        )

    if response.status == AIResponseStatus.RATE_LIMITED:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=response.error_message or "Gemini API rate limit or quota exceeded.",
        )

    return response
