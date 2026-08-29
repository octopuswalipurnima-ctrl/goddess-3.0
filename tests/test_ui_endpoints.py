"""Comprehensive tests for testing web console UI, video ID parsing, and API endpoints."""

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import close_engine, init_engine
from app.gemini import GeminiClient, GeminiKeyPool
from app.main import app
from app.utils import parse_youtube_video_id
from app.workers import OutboundMessageQueue, StreamManager
from app.youtube import YouTubeClient, YouTubeKeyPool


def test_parse_youtube_video_id_formats():
    """Verify robust extraction of 11-char YouTube video ID across various URL formats."""
    # 1. Standard watch URL
    assert parse_youtube_video_id("https://www.youtube.com/watch?v=g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    # 2. Watch URL with query parameters
    assert (
        parse_youtube_video_id("https://www.youtube.com/watch?v=g4Qb5C_Wnf0&feature=share&t=10s")
        == "g4Qb5C_Wnf0"
    )
    # 3. Shortened youtu.be URL
    assert parse_youtube_video_id("https://youtu.be/g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    assert parse_youtube_video_id("https://youtu.be/g4Qb5C_Wnf0?si=abc123xyz") == "g4Qb5C_Wnf0"
    # 4. Live URL
    assert parse_youtube_video_id("https://www.youtube.com/live/g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    assert parse_youtube_video_id("https://youtube.com/live/g4Qb5C_Wnf0?feature=share") == "g4Qb5C_Wnf0"
    # 5. Embed URL
    assert parse_youtube_video_id("https://www.youtube.com/embed/g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    # 6. Mobile URL
    assert parse_youtube_video_id("https://m.youtube.com/watch?v=g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    # 7. Raw Video ID
    assert parse_youtube_video_id("g4Qb5C_Wnf0") == "g4Qb5C_Wnf0"
    # 8. Invalid formats
    assert parse_youtube_video_id("") is None
    assert parse_youtube_video_id(None) is None
    assert parse_youtube_video_id("https://google.com") is None
    assert parse_youtube_video_id("short_id") is None


@pytest.mark.asyncio
async def test_ui_endpoints_html_and_json_negotiation():
    """Verify / and /test serve HTML console and accept header returns JSON identity."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Browser request to /
        resp_html = await client.get("/", headers={"accept": "text/html,application/xhtml+xml"})
        assert resp_html.status_code == 200
        assert "text/html" in resp_html.headers.get("content-type", "")
        assert "Goddess AI 3.0" in resp_html.text
        assert "Connect Bot to Live Stream" in resp_html.text

        # Browser request to /test
        resp_test = await client.get("/test")
        assert resp_test.status_code == 200
        assert "text/html" in resp_test.headers.get("content-type", "")
        assert "YouTube Live Stream Link" in resp_test.text

        # API JSON request to /
        resp_json = await client.get("/", headers={"accept": "application/json"})
        assert resp_json.status_code == 200
        assert resp_json.headers.get("content-type", "").startswith("application/json")
        data = resp_json.json()
        assert data["app"] == "Goddess AI 3.0"
        assert data["cohost"] == "Honney"


@pytest.mark.asyncio
async def test_api_status_endpoint():
    """Verify /api/status returns real-time status and configured channels."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["app"] == "Goddess AI 3.0"
        assert "database" in data
        assert "active_streams" in data
        assert "configured_channels" in data
        assert len(data["configured_channels"]) >= 1


@pytest.mark.asyncio
async def test_stream_manager_manual_connect_and_disconnect():
    """Verify StreamManager.connect_manual_stream parses URL, resolves live chat, starts worker, and disconnects."""
    init_engine()

    class MockTestLiveTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "/youtube/v3/videos" in url_str:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "g4Qb5C_Wnf0",
                                "snippet": {
                                    "title": "Misayuislive Gaming Night",
                                    "channelId": "UCCMwadkzXrznmMpZd5ek6PA",
                                    "channelTitle": "Misayuislive",
                                    "liveBroadcastContent": "live",
                                },
                                "liveStreamingDetails": {
                                    "activeLiveChatId": "chat_g4Qb5C_Wnf0",
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

    http_client = httpx.AsyncClient(transport=MockTestLiveTransport())
    yt = YouTubeClient(key_pool=YouTubeKeyPool(["k1"]), http_client=http_client)
    outbound = OutboundMessageQueue(youtube_client=yt)
    mgr = StreamManager(
        youtube_client=yt,
        gemini_client=GeminiClient(key_pool=GeminiKeyPool([])),
        outbound_queue=outbound,
    )

    # 1. Connect via full YouTube watch URL
    result = await mgr.connect_manual_stream("https://www.youtube.com/watch?v=g4Qb5C_Wnf0")
    assert result["success"] is True
    assert result["video_id"] == "g4Qb5C_Wnf0"
    assert result["channel_id"] == "UCCMwadkzXrznmMpZd5ek6PA"
    assert result["live_chat_id"] == "chat_g4Qb5C_Wnf0"

    # Verify active status
    status_list = mgr.get_active_streams_status()
    assert len(status_list) == 1
    assert status_list[0]["video_id"] == "g4Qb5C_Wnf0"

    # 2. Duplicate connect attempt reports ALREADY_CONNECTED
    dup_res = await mgr.connect_manual_stream("https://youtu.be/g4Qb5C_Wnf0")
    assert dup_res["success"] is True
    assert dup_res["status"] == "ALREADY_CONNECTED"

    # 3. Disconnect
    dis_res = await mgr.disconnect_stream("g4Qb5C_Wnf0")
    assert dis_res["success"] is True
    assert len(mgr.get_active_streams_status()) == 0

    await mgr.stop()
    await yt.close()
    await close_engine()
