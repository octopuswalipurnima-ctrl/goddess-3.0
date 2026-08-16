"""
Tests for Streams REST API Endpoints and WebSub Webhook Routes.
"""

import pytest
from httpx import AsyncClient
from app.services.youtube import stream_manager
from app.services.youtube.models import LiveStreamInfo, StreamStatus


class MockAPIClient:
    """Mock client for FastAPI integration tests."""

    async def get_live_stream_details(self, stream_id: str):
        return LiveStreamInfo(
            stream_id=stream_id,
            channel_id="UC_test_ch",
            title="FastAPI Test Stream",
            status=StreamStatus.LIVE,
            concurrent_viewers=120,
            live_chat_id="chat_api_123",
        )

    async def send_chat_message(self, live_chat_id: str, message_text: str):
        from app.services.youtube.models import ChatMessage
        return ChatMessage(
            message_id="msg_api_sent_1",
            stream_id=live_chat_id,
            channel_id="UC_test_ch",
            author_id="bot_id",
            author_name="GoddessBot",
            message_text=message_text,
            published_at="2026-08-16T12:00:00Z",
        )

    async def get_live_chat_messages(self, live_chat_id: str, page_token: str = None):
        return [], None, 1000


@pytest.mark.asyncio
async def test_streams_api_crud_flow(async_client: AsyncClient, monkeypatch):
    """Verify listing, creating, posting chat, and stopping a stream via API."""
    # Inject mock client into global stream_manager
    monkeypatch.setattr(stream_manager, "client", MockAPIClient())

    # 1. List streams initially (empty)
    res = await async_client.get("/api/v1/streams")
    assert res.status_code == 200

    # 2. Create stream session
    payload = {"stream_id": "test_stream_api_1", "auto_start": True}
    create_res = await async_client.post("/api/v1/streams", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["stream_id"] == "test_stream_api_1"
    assert created_data["status"] == "LIVE"

    # 3. Get stream detail
    detail_res = await async_client.get("/api/v1/streams/test_stream_api_1")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "FastAPI Test Stream"

    # 4. Post chat message to stream
    chat_res = await async_client.post(
        "/api/v1/streams/test_stream_api_1/chat",
        json={"message": "Broadcast from API test!"},
    )
    assert chat_res.status_code == 200
    assert chat_res.json()["message_text"] == "Broadcast from API test!"

    # 5. Stop stream
    stop_res = await async_client.post("/api/v1/streams/test_stream_api_1/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "success"


@pytest.mark.asyncio
async def test_websub_challenge_verification_endpoint(async_client: AsyncClient):
    """Verify WebSub hub challenge response."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "random_challenge_string_12345",
        "hub.topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC123",
    }
    res = await async_client.get("/api/v1/streams/webhook", params=params)
    assert res.status_code == 200
    assert res.text == "random_challenge_string_12345"


@pytest.mark.asyncio
async def test_health_telemetry_with_youtube_service(async_client: AsyncClient):
    """Verify health endpoint includes YouTube subsystem telemetry."""
    res = await async_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "youtube" in data["components"]
    yt_health = data["components"]["youtube"]
    assert "metadata" in yt_health
    assert "max_streams" in yt_health["metadata"]
    assert yt_health["metadata"]["max_streams"] == 4
