"""Comprehensive tests for Misayuislive auto-detection, stream lifecycle, idempotent join message, and !scanlive command."""

import httpx
import pytest
from sqlalchemy import select

from app.commands import CommandContext, PermissionLevel, registry
from app.config import settings
from app.database import get_session
from app.gemini import GeminiClient, GeminiKeyPool
from app.models import AuditLog, ChannelSettings, Stream
from app.workers import (
    ChatWorker,
    OutboundMessageQueue,
    StreamManager,
    WorkerState,
)
from app.youtube import (
    LiveDetectionResult,
    LiveDetectionStatus,
    OAuthManager,
    YouTubeClient,
    YouTubeKeyPool,
)

MISAYU_UC_ID = "UCCMwadkzXrznmMpZd5ek6PA"


@pytest.mark.asyncio
async def test_misayuislive_channel_config_loaded():
    """Verify Misayuislive is present in channels.json with permanent UC ID."""
    channels = settings.load_channels()
    misayu = next((c for c in channels if c.channel_id == MISAYU_UC_ID), None)
    assert misayu is not None, f"Channel {MISAYU_UC_ID} not found in channels.json!"
    assert misayu.channel_id.startswith("UC")
    assert misayu.enabled is True
    assert misayu.auto_join is True


@pytest.mark.asyncio
async def test_offline_channel_detection():
    """Verify offline channel scan returns OFFLINE without starting worker."""

    class MockOfflineTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if "/youtube/v3/search" in str(request.url):
                return httpx.Response(200, json={"items": []}, request=request)
            return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=MockOfflineTransport())
    yt_client = YouTubeClient(
        key_pool=YouTubeKeyPool(["test_key"]),
        http_client=client,
    )
    gemini_client = GeminiClient(key_pool=GeminiKeyPool([]))
    outbound = OutboundMessageQueue(youtube_client=yt_client)
    stream_mgr = StreamManager(
        youtube_client=yt_client,
        gemini_client=gemini_client,
        outbound_queue=outbound,
    )

    res = await stream_mgr.scan_channel(MISAYU_UC_ID)
    assert res.status == "OFFLINE"
    assert res.is_offline is True
    assert MISAYU_UC_ID not in stream_mgr._workers

    await stream_mgr.stop()
    await yt_client.close()


@pytest.mark.asyncio
async def test_live_detection_and_idempotent_join_message():
    """
    Verify complete live detection flow:
    - active broadcast detected
    - liveChatId resolved
    - ChatWorker started
    - Exactly ONE join greeting sent via OAuth
    - Stream.join_message_sent set to True
    - Duplicate detection does not re-send join message
    """
    posted_messages = []

    class MockLiveTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/search" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {"videoId": "misayu_live_vid_1"},
                                "snippet": {"title": "Misayuislive Gaming Stream!"},
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "misayu_live_vid_1",
                                "liveStreamingDetails": {
                                    "activeLiveChatId": "chat_id_misayu_999",
                                },
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/liveChat/messages" in url_str and request.method == "POST":
                posted_messages.append(request.read().decode())
                return httpx.Response(200, json={"id": "sent_msg_123"}, request=request)
            elif "/youtube/v3/liveChat/messages" in url_str and request.method == "GET":
                return httpx.Response(
                    200,
                    json={"items": [], "pollingIntervalMillis": 5000},
                    request=request,
                )
            return httpx.Response(404, request=request)

    http_client = httpx.AsyncClient(transport=MockLiveTransport())
    oauth_mgr = OAuthManager(
        client_id="cid",
        client_secret="sec",
        access_token="valid_token",
        refresh_token="ref_token",
    )
    yt_client = YouTubeClient(
        key_pool=YouTubeKeyPool(["test_key"]),
        oauth_manager=oauth_mgr,
        http_client=http_client,
    )
    gemini_client = GeminiClient(key_pool=GeminiKeyPool([]))
    outbound = OutboundMessageQueue(youtube_client=yt_client)
    stream_mgr = StreamManager(
        youtube_client=yt_client,
        gemini_client=gemini_client,
        outbound_queue=outbound,
    )

    # 1. Trigger live scan
    res = await stream_mgr.scan_channel(MISAYU_UC_ID)
    assert res.status == "LIVE"
    assert res.is_live is True
    assert res.video_id == "misayu_live_vid_1"

    # Verify worker was started
    assert MISAYU_UC_ID in stream_mgr._workers
    worker = stream_mgr._workers[MISAYU_UC_ID]
    assert worker._running is True
    assert worker.live_chat_id == "chat_id_misayu_999"

    # Verify ONE join message was posted
    assert len(posted_messages) == 1
    assert settings.JOIN_MESSAGE in posted_messages[0]

    # Verify database state
    async with get_session() as session:
        stmt = select(Stream).where(Stream.youtube_video_id == "misayu_live_vid_1")
        s_res = await session.execute(stmt)
        stream = s_res.scalar_one_or_none()
        assert stream is not None
        assert stream.status == "LIVE"
        assert stream.join_message_sent is True

        # Verify audit log entry
        a_stmt = select(AuditLog).where(
            AuditLog.channel_id == MISAYU_UC_ID,
            AuditLog.command == "SYSTEM_JOIN_MESSAGE",
        )
        a_res = await session.execute(a_stmt)
        audit = a_res.scalar_one_or_none()
        assert audit is not None
        assert audit.result == "SUCCESS"

    # 2. Trigger second scan (duplicate) -> Must NOT send join message again
    res2 = await stream_mgr.scan_channel(MISAYU_UC_ID)
    assert res2.status == "LIVE"
    assert len(posted_messages) == 1  # Still exactly 1!

    # 3. Simulate WebSub duplicate notification -> Must NOT send join message again
    await stream_mgr.on_video_detected(MISAYU_UC_ID, "misayu_live_vid_1")
    assert len(posted_messages) == 1

    await stream_mgr.stop()
    await yt_client.close()


@pytest.mark.asyncio
async def test_manual_scanlive_command():
    """Verify !scanlive command scans channel and returns friendly response."""

    class MockScanTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if "/youtube/v3/search" in str(request.url):
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {"videoId": "vid_live_123"},
                                "snippet": {"title": "Live Broadcast"},
                            }
                        ]
                    },
                    request=request,
                )
            return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=MockScanTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["test_key"]), http_client=client)

    async with get_session() as session:
        ch_settings = ChannelSettings(channel_id=MISAYU_UC_ID)
        ctx = CommandContext(
            session=session,
            channel_id=MISAYU_UC_ID,
            stream_id=1,
            live_chat_id="chat_1",
            author_id="mod_user_1",
            author_name="Moderator",
            permission=PermissionLevel.MODERATOR,
            channel_settings=ch_settings,
            youtube_client=yt,
        )

        reply = await registry.execute("!scanlive", ctx)
        assert reply is not None
        assert "Live detected!" in reply

    await yt.close()


@pytest.mark.asyncio
async def test_stream_conclusion_stops_worker_and_new_stream_creates_new_lifecycle():
    """Verify stream ending marks ENDED, stops ChatWorker, and next video starts new cycle."""

    class MockMultiStreamTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.current_video = "vid_session_1"

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/search" in url_str:
                if self.current_video:
                    return httpx.Response(
                        200,
                        json={
                            "items": [
                                {
                                    "id": {"videoId": self.current_video},
                                    "snippet": {"title": f"Stream {self.current_video}"},
                                }
                            ]
                        },
                        request=request,
                    )
                return httpx.Response(200, json={"items": []}, request=request)
            elif "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": self.current_video,
                                "liveStreamingDetails": {
                                    "activeLiveChatId": f"chat_{self.current_video}",
                                },
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/liveChat/messages" in url_str:
                return httpx.Response(
                    200,
                    json={"items": [], "pollingIntervalMillis": 5000},
                    request=request,
                )
            return httpx.Response(404, request=request)

    transport = MockMultiStreamTransport()
    client = httpx.AsyncClient(transport=transport)
    oauth = OAuthManager(
        client_id="c",
        client_secret="s",
        access_token="tok",
        refresh_token="ref",
    )
    yt = YouTubeClient(
        key_pool=YouTubeKeyPool(["k1"]),
        oauth_manager=oauth,
        http_client=client,
    )
    stream_mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=OutboundMessageQueue(youtube_client=yt),
    )

    # 1. Start stream 1
    await stream_mgr.scan_channel(MISAYU_UC_ID)
    assert MISAYU_UC_ID in stream_mgr._workers
    w1 = stream_mgr._workers[MISAYU_UC_ID]
    assert w1.video_id == "vid_session_1"

    # 2. Conclude stream 1
    await w1._handle_stream_end()
    async with get_session() as session:
        stmt = select(Stream).where(Stream.youtube_video_id == "vid_session_1")
        s = (await session.execute(stmt)).scalar_one()
        assert s.status == "ENDED"
        assert s.ended_at is not None

    # 3. Start stream 2 (new video ID)
    transport.current_video = "vid_session_2"
    await stream_mgr.scan_channel(MISAYU_UC_ID)
    w2 = stream_mgr._workers[MISAYU_UC_ID]
    assert w2.video_id == "vid_session_2"

    async with get_session() as session:
        stmt2 = select(Stream).where(Stream.youtube_video_id == "vid_session_2")
        s2 = (await session.execute(stmt2)).scalar_one()
        assert s2.status == "LIVE"
        assert s2.youtube_video_id == "vid_session_2"

    await stream_mgr.stop()
    await yt.close()


@pytest.mark.asyncio
async def test_nawaabo_channel_scan_live_detection():
    """Verify live detection for channel UCVQ8Qn1JPuZV8VzOgIdUGxQ when active."""
    nawaabo_id = "UCVQ8Qn1JPuZV8VzOgIdUGxQ"

    class MockNawaaboLiveTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/search" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": {"videoId": "nawaabo_live_vid"},
                                "snippet": {"title": "Nawaabo Live Stream"},
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "nawaabo_live_vid",
                                "liveStreamingDetails": {
                                    "activeLiveChatId": "chat_nawaabo_live",
                                },
                            }
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/liveChat/messages" in url_str:
                return httpx.Response(
                    200,
                    json={"items": [], "pollingIntervalMillis": 5000},
                    request=request,
                )
            return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=MockNawaaboLiveTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)
    stream_mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=OutboundMessageQueue(youtube_client=yt),
    )

    res = await stream_mgr.scan_channel(nawaabo_id)
    assert res.status == "LIVE"
    assert res.is_live is True
    assert res.video_id == "nawaabo_live_vid"
    assert nawaabo_id in stream_mgr._workers

    await stream_mgr.stop()
    await yt.close()


@pytest.mark.asyncio
async def test_api_error_does_not_mark_channel_offline_in_stream_manager():
    """Verify that when YouTube API fails with quota/network error, StreamManager does NOT report OFFLINE."""
    nawaabo_id = "UCVQ8Qn1JPuZV8VzOgIdUGxQ"

    class MockFailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={
                    "error": {
                        "code": 403,
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockFailingTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)
    stream_mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=OutboundMessageQueue(youtube_client=yt),
    )

    res = await stream_mgr.scan_channel(nawaabo_id)
    assert res.status != "OFFLINE"
    assert res.is_offline is False
    assert res.status == "QUOTA_ERROR"
    assert res.is_error is True

    await stream_mgr.stop()
    await yt.close()


@pytest.mark.asyncio
async def test_join_message_failure_preserves_false_state():
    """Verify that if post_chat_message fails, join_message_sent remains False and can retry."""
    channel_id = "UCCMwadkzXrznmMpZd5ek6PA"
    video_id = "vid_fail_join_1"

    class MockFailJoinTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/search" in url_str:
                return httpx.Response(
                    200,
                    json={"items": [{"id": {"videoId": video_id}, "snippet": {"title": "Test"}}]},
                    request=request,
                )
            elif "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"id": video_id, "liveStreamingDetails": {"activeLiveChatId": "chat_fail_1"}}
                        ]
                    },
                    request=request,
                )
            elif "/youtube/v3/liveChat/messages" in url_str and request.method == "POST":
                # Simulate 403 Forbidden on message insert
                return httpx.Response(403, json={"error": {"message": "Chat disabled"}}, request=request)
            elif "/youtube/v3/liveChat/messages" in url_str and request.method == "GET":
                return httpx.Response(200, json={"items": [], "pollingIntervalMillis": 5000}, request=request)
            return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=MockFailJoinTransport())
    oauth_mgr = OAuthManager(
        client_id="cid",
        client_secret="sec",
        access_token="tok",
        refresh_token="ref",
    )
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), oauth_manager=oauth_mgr, http_client=client)
    stream_mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=OutboundMessageQueue(youtube_client=yt),
    )

    res = await stream_mgr.scan_channel(channel_id)
    assert res.status == "LIVE"

    # Database check: join_message_sent MUST be False
    async with get_session() as session:
        stmt = select(Stream).where(Stream.youtube_video_id == video_id)
        s_obj = (await session.execute(stmt)).scalar_one()
        assert s_obj.join_message_sent is False

    await stream_mgr.stop()
    await yt.close()


@pytest.mark.asyncio
async def test_chat_worker_lifecycle_states():
    """Verify ChatWorker lifecycle state transitions: STOPPED -> STARTING -> RUNNING -> STOPPED."""

    class MockPollTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "msg_1", "snippet": {"displayMessage": "Hi"}}],
                    "pollingIntervalMillis": 5000,
                },
                request=request,
            )

    client = httpx.AsyncClient(transport=MockPollTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=client)
    outbound = OutboundMessageQueue(youtube_client=yt)
    worker = ChatWorker(
        channel_id="UC_TEST",
        video_id="VID_TEST",
        live_chat_id="CHAT_TEST",
        stream_id=999,
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=outbound,
    )

    assert worker.state == WorkerState.STOPPED
    worker.start()
    assert worker.state in (WorkerState.STARTING, WorkerState.RUNNING)

    # Let the first poll loop tick
    import asyncio

    await asyncio.sleep(0.05)
    assert worker.state == WorkerState.RUNNING
    assert worker._first_poll_done is True

    await worker.stop()
    assert worker.state == WorkerState.STOPPED
    await yt.close()


@pytest.mark.asyncio
async def test_channel_reconciliation_error_isolation(monkeypatch):
    """Verify that if one channel throws an unhandled database/API exception, other channels still reconcile."""
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]))
    stream_mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=OutboundMessageQueue(youtube_client=yt),
    )

    async def mock_scan(channel_id: str) -> LiveDetectionResult:
        if channel_id == "UCCMwadkzXrznmMpZd5ek6PA":
            raise RuntimeError("Simulated database timeout on channel scan")
        return LiveDetectionResult(status=LiveDetectionStatus.OFFLINE, channel_id=channel_id)

    monkeypatch.setattr(stream_mgr, "scan_channel", mock_scan)

    results = await stream_mgr.scan_all_channels_now()
    # The failing channel did not abort the loop:
    assert "UCVQ8Qn1JPuZV8VzOgIdUGxQ" in results
    assert results["UCVQ8Qn1JPuZV8VzOgIdUGxQ"].status == "OFFLINE"

    await stream_mgr.stop()
    await yt.close()
