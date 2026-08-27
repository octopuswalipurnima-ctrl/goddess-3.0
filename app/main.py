"""FastAPI main application entrypoint, lifecycle management, health checks, and WebSub endpoints."""

import hashlib
import hmac
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.config import settings
from app.database import (
    close_engine,
    get_session,
    init_engine,
    verify_database_connection,
)
from app.gemini import GeminiClient, GeminiKeyPool
from app.models import Channel, ChannelSettings
from app.utils import get_logger, setup_logging
from app.workers import (
    OutboundMessageQueue,
    StreamManager,
    WebSubManager,
    parse_websub_xml_feed,
)
from app.youtube import OAuthManager, YouTubeClient, YouTubeKeyPool

logger = get_logger("goddess.main")

# Global subsystem singletons
youtube_client: YouTubeClient | None = None
gemini_client: GeminiClient | None = None
outbound_queue: OutboundMessageQueue | None = None
stream_manager: StreamManager | None = None
websub_manager: WebSubManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and graceful shutdown lifecycle handler."""
    global youtube_client, gemini_client, outbound_queue, stream_manager, websub_manager

    setup_logging()
    logger.info("Starting Goddess AI 3.0 (Honney)...")
    settings.log_summary()

    # 1. Database initialization and connectivity verification
    try:
        init_engine()
        db_ok, db_diag = await verify_database_connection(timeout_seconds=5.0)
        if not db_ok:
            logger.error(f"DATABASE STARTUP VERIFICATION FAILED: {db_diag}")
            if settings.is_production:
                raise RuntimeError(
                    f"Production database connection failure: {db_diag}. "
                    "Verify DATABASE_URL is set in your Railway service variables."
                )
        else:
            logger.info("Database startup verification succeeded.")
    except Exception as e:
        logger.error(f"Fatal error during database startup: {e}")
        raise

    # 2. Sync configured channels to DB
    async with get_session() as session:
        channels_config = settings.load_channels()
        for ch_cfg in channels_config:
            stmt = select(Channel).where(Channel.channel_id == ch_cfg.channel_id)
            res = await session.execute(stmt)
            ch = res.scalar_one_or_none()
            if not ch:
                ch = Channel(
                    channel_id=ch_cfg.channel_id,
                    name=ch_cfg.name,
                    enabled=ch_cfg.enabled,
                )
                session.add(ch)
                await session.flush()
                # Create default settings
                s = ChannelSettings(channel_id=ch_cfg.channel_id)
                session.add(s)
            else:
                ch.name = ch_cfg.name
                ch.enabled = ch_cfg.enabled

    # 3. YouTube Client & Key Pool
    yt_pool = YouTubeKeyPool(settings.get_youtube_keys())
    oauth_mgr = OAuthManager(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        access_token=settings.YOUTUBE_OAUTH_TOKEN,
        refresh_token=settings.YOUTUBE_OAUTH_REFRESH_TOKEN,
    )
    youtube_client = YouTubeClient(key_pool=yt_pool, oauth_manager=oauth_mgr)

    # 4. Gemini Client & Key Pool
    gemini_pool = GeminiKeyPool(settings.get_gemini_keys())
    gemini_client = GeminiClient(key_pool=gemini_pool)

    # 5. Outbound Queue & Workers
    outbound_queue = OutboundMessageQueue(youtube_client=youtube_client)
    stream_manager = StreamManager(
        youtube_client=youtube_client,
        gemini_client=gemini_client,
        outbound_queue=outbound_queue,
    )
    websub_manager = WebSubManager()

    # Start background managers
    stream_manager.start()
    websub_manager.start()

    logger.info("Goddess AI 3.0 initialized successfully and running.")
    yield

    # Shutdown
    logger.info("Shutting down Goddess AI 3.0...")
    if websub_manager:
        await websub_manager.stop()
    if stream_manager:
        await stream_manager.stop()
    if youtube_client:
        await youtube_client.close()
    if gemini_client:
        await gemini_client.close()
    await close_engine()
    logger.info("Goddess AI 3.0 shutdown complete.")


app = FastAPI(
    title="Goddess AI 3.0 (Honney)",
    description="YouTube Live AI Co-Host, Adaptive Hindi/Hinglish Moderation & 1v1 Queue",
    version="3.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    """Basic root service identity."""
    return {
        "app": "Goddess AI 3.0",
        "cohost": "Honney",
        "status": "online",
        "ui": "YouTube Live Chat",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic process health and safe database status check."""
    is_configured = bool(settings.get_database_url_safe())
    db_ok, _ = await verify_database_connection(timeout_seconds=2.0)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": {
            "configured": is_configured,
            "connected": db_ok,
        },
    }


@app.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Deep readiness check validating database, API pools, and OAuth."""
    is_configured = bool(settings.get_database_url_safe())
    db_ok, db_diag = await verify_database_connection(timeout_seconds=3.0)

    yt_healthy = youtube_client.key_pool.get_healthy_count() if youtube_client else 0
    gemini_healthy = gemini_client.key_pool.get_healthy_count() if gemini_client else 0
    oauth_ready = youtube_client.oauth.is_configured if youtube_client else False

    is_ready = db_ok and (yt_healthy > 0 or gemini_healthy > 0 or not settings.get_youtube_keys())

    response_data = {
        "status": "ready" if is_ready else "degraded",
        "database": {
            "configured": is_configured,
            "connected": db_ok,
            "detail": db_diag,
        },
        "youtube_api_keys_healthy": yt_healthy,
        "gemini_api_keys_healthy": gemini_healthy,
        "oauth_configured": oauth_ready,
        "websub_callback": bool(settings.WEBSUB_CALLBACK_URL),
    }

    if not is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response_data)

    return response_data


# ---------------------------------------------------------------------------
# WebSub Endpoints (PubSubHubbub)
# ---------------------------------------------------------------------------


@app.get("/websub/youtube", response_class=PlainTextResponse)
async def websub_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_topic: str = Query(..., alias="hub.topic"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_lease_seconds: int | None = Query(default=None, alias="hub.lease_seconds"),
) -> str:
    """Handle WebSub hub challenge verification."""
    logger.info(f"Received WebSub verification request: mode={hub_mode} topic={hub_topic}")
    if hub_mode in ("subscribe", "unsubscribe"):
        return hub_challenge
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported hub.mode")


@app.post("/websub/youtube")
async def websub_notification(request: Request) -> Response:
    """Handle incoming WebSub YouTube push notification."""
    body_bytes = await request.body()

    # Verify HMAC signature if secret and header are present
    sig_header = request.headers.get("X-Hub-Signature")
    if sig_header and settings.WEBSUB_SECRET:
        expected_sig = (
            "sha1="
            + hmac.new(
                settings.WEBSUB_SECRET.encode("utf-8"),
                body_bytes,
                hashlib.sha1,
            ).hexdigest()
        )
        if not hmac.compare_digest(sig_header, expected_sig):
            logger.warning("WebSub notification HMAC signature mismatch!")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    channel_id, video_id = parse_websub_xml_feed(body_bytes)
    if channel_id and video_id:
        logger.info(f"WebSub feed parsed: channel_id={channel_id} video_id={video_id}")
        if stream_manager:
            await stream_manager.on_video_detected(channel_id, video_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
