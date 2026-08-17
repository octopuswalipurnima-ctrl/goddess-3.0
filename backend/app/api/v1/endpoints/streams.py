"""
Streams & YouTube Live REST Endpoints for GODDESS AI 2.0.

Provides endpoints to list active stream sessions, connect/stop streams, post chat messages,
manage StreamSupervisor lifecycle, and control stream/global emergency stop and safe mode.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.auth.dependencies import require_permission
from app.core.safety_controller import safety_controller
from app.services.youtube import (
    ChatMessage,
    ChatMessageValidationError,
    DuplicateStreamError,
    LiveChatUnavailableError,
    MaxStreamsReachedError,
    StreamNotFoundError,
    StreamSessionSummary,
    live_detector,
    stream_manager,
)
from app.services.youtube.stream_supervisor import (
    StreamSupervisorSummary,
    stream_supervisor,
)

router = APIRouter(prefix="/streams", tags=["Streams"])


class CreateStreamRequest(BaseModel):
    stream_id: str = Field(..., description="YouTube Live Video/Stream ID or URL", min_length=1)
    channel_id: Optional[str] = Field(default=None, description="Optional YouTube Channel ID")
    auto_start: bool = Field(default=True, description="Whether to automatically connect to live chat")


class PostChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=200, description="Chat message text (max 200 chars)")


class EmergencyStopRequest(BaseModel):
    reason: str = Field(default="Operator emergency stop", min_length=1, max_length=255)


class SafeModeRequest(BaseModel):
    reason: str = Field(default="Operator enabled safe mode", min_length=1, max_length=255)


@router.get(
    "",
    response_model=List[StreamSessionSummary],
    dependencies=[Depends(require_permission("stream.read"))],
    summary="List Active Stream Sessions",
)
async def list_streams():
    """Get summaries for all currently tracked YouTube live stream sessions."""
    return stream_manager.list_sessions()


@router.get(
    "/supervised",
    response_model=List[StreamSupervisorSummary],
    dependencies=[Depends(require_permission("stream.read"))],
    summary="List Supervised Stream Sessions",
)
async def list_supervised_streams():
    """Get summaries for all currently supervised YouTube live stream sessions."""
    return stream_supervisor.list_supervisor_sessions()


@router.post(
    "",
    response_model=StreamSessionSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Connect New Live Stream",
)
async def create_stream(request: CreateStreamRequest):
    """
    Register and start monitoring a YouTube live stream session.
    Enforces maximum concurrent capacity limit (4 streams) and prevents duplicates.
    """
    try:
        session = await stream_manager.create_session(
            stream_id=request.stream_id,
            channel_id=request.channel_id,
            auto_start=request.auto_start,
        )
        return session.to_summary()

    except DuplicateStreamError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except MaxStreamsReachedError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except StreamNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize stream session: {str(e)}",
        )


@router.post(
    "/attach",
    response_model=StreamSupervisorSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Attach Stream to Supervisor",
)
async def attach_stream(request: CreateStreamRequest):
    """Attach and start supervising a YouTube live stream session."""
    try:
        sup_session = await stream_supervisor.attach_stream(
            stream_id=request.stream_id,
            channel_id=request.channel_id,
            auto_start=request.auto_start,
        )
        return sup_session.to_summary()
    except DuplicateStreamError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except MaxStreamsReachedError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{stream_id}/detach",
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Detach Stream from Supervisor",
)
async def detach_stream(stream_id: str):
    """Detach and stop supervising a live stream session."""
    detached = await stream_supervisor.detach_stream(stream_id, reason="Detached via API")
    if not detached:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Supervised stream '{stream_id}' not found.")
    return {"status": "success", "message": f"Stream '{stream_id}' detached successfully."}


@router.post(
    "/{stream_id}/reconnect",
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Reconnect Supervised Stream",
)
async def reconnect_stream(stream_id: str):
    """Trigger a controlled reconnection for a supervised stream."""
    success = await stream_supervisor.reconnect_stream(stream_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reconnection failed or stream '{stream_id}' not found.",
        )
    return {"status": "success", "message": f"Stream '{stream_id}' reconnected."}


# --- Emergency Controls & Safe Mode ---


@router.post(
    "/global-emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Trigger Global Emergency Stop",
)
async def trigger_global_emergency_stop(request: EmergencyStopRequest):
    """Trigger system-wide emergency halt halting all automated external actions."""
    await safety_controller.trigger_emergency_stop(stream_id=None, reason=request.reason)
    return {"status": "EMERGENCY_STOP", "message": "Global emergency stop activated."}


@router.post(
    "/clear-global-emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Clear Global Emergency Stop",
)
async def clear_global_emergency_stop():
    """Clear global emergency halt and restore NORMAL operation."""
    await safety_controller.clear_emergency_stop(stream_id=None)
    return {"status": "NORMAL", "message": "Global emergency stop cleared."}


@router.post(
    "/{stream_id}/emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Trigger Stream Emergency Stop",
)
async def trigger_stream_emergency_stop(stream_id: str, request: EmergencyStopRequest):
    """Halt all automated actions on a specific live stream."""
    await safety_controller.trigger_emergency_stop(stream_id=stream_id, reason=request.reason)
    return {"status": "EMERGENCY_STOP", "stream_id": stream_id, "message": f"Emergency stop activated on '{stream_id}'."}


@router.post(
    "/{stream_id}/clear-emergency-stop",
    dependencies=[Depends(require_permission("moderation.emergency"))],
    summary="Clear Stream Emergency Stop",
)
async def clear_stream_emergency_stop(stream_id: str):
    """Clear emergency halt on a specific live stream."""
    await safety_controller.clear_emergency_stop(stream_id=stream_id)
    return {"status": "NORMAL", "stream_id": stream_id, "message": f"Emergency stop cleared on '{stream_id}'."}


@router.post(
    "/{stream_id}/safe-mode",
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Enable Stream Safe Mode",
)
async def enable_stream_safe_mode(stream_id: str, request: SafeModeRequest):
    """Put a specific live stream into safe mode (restricts automated mutations and AI replies)."""
    await safety_controller.enable_safe_mode(stream_id=stream_id, reason=request.reason)
    return {"status": "SAFE_MODE", "stream_id": stream_id, "message": f"Safe mode enabled on '{stream_id}'."}


@router.post(
    "/{stream_id}/clear-safe-mode",
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Disable Stream Safe Mode",
)
async def disable_stream_safe_mode(stream_id: str):
    """Restore normal automated operations on a specific live stream."""
    await safety_controller.disable_safe_mode(stream_id=stream_id)
    return {"status": "NORMAL", "stream_id": stream_id, "message": f"Safe mode disabled on '{stream_id}'."}


@router.get("/webhook", summary="WebSub Hub Challenge Verification")
async def websub_challenge_verify(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_topic: Optional[str] = Query(None, alias="hub.topic"),
):
    """Responds to Google WebSub subscription verification challenge."""
    if hub_mode in ["subscribe", "unsubscribe"] and hub_challenge:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Invalid challenge")


@router.post("/webhook", summary="WebSub Live Detection Webhook Notification")
async def websub_notification_receiver(
    request: Request,
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature"),
):
    """Receives and processes YouTube WebSub Atom XML push notifications."""
    body_bytes = await request.body()
    raw_xml = body_bytes.decode("utf-8", errors="replace")

    video_id = await live_detector.handle_webhook_notification(
        raw_xml, signature_header=x_hub_signature
    )
    return {"status": "received", "video_id": video_id}


@router.get(
    "/{stream_id}",
    response_model=StreamSessionSummary,
    dependencies=[Depends(require_permission("stream.read"))],
    summary="Get Stream Session Details",
)
async def get_stream(stream_id: str):
    """Get detailed status and metrics for a specific stream session."""
    session = stream_manager.get_session(stream_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream session '{stream_id}' not found.",
        )
    return session.to_summary()


@router.post(
    "/{stream_id}/stop",
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Stop Live Stream Session",
)
async def stop_stream(stream_id: str):
    """Stop live chat polling and disconnect a stream session."""
    stopped = await stream_manager.stop_session(stream_id, reason="Stopped via API")
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream session '{stream_id}' not found.",
        )
    return {"status": "success", "message": f"Stream session '{stream_id}' stopped."}


@router.post(
    "/{stream_id}/chat",
    response_model=ChatMessage,
    dependencies=[Depends(require_permission("stream.control"))],
    summary="Post Live Chat Message",
)
async def post_chat_message(stream_id: str, request: PostChatMessageRequest):
    """Post an outgoing message to the stream's YouTube Live Chat."""
    session = stream_manager.get_session(stream_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream session '{stream_id}' not found.",
        )

    try:
        sent_msg = await session.send_chat_message(request.message)
        return sent_msg
    except ChatMessageValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except LiveChatUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post chat message: {str(e)}",
        )
