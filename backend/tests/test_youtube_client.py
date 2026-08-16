"""
Tests for YouTube API Client with Mock HTTP Transports.
"""

import pytest
import httpx
from app.services.youtube.client import YouTubeAPIClient
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.exceptions import (
    ChatMessageValidationError,
    QuotaExceededError,
    StreamNotFoundError,
)
from app.services.youtube.models import StreamStatus


@pytest.mark.asyncio
async def test_get_live_stream_details_success():
    """Verify live stream details parsing from mock YouTube response."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = {
            "items": [
                {
                    "id": "video_abc_123",
                    "snippet": {
                        "channelId": "UC_channel_123",
                        "title": "Goddess AI Live Stream",
                        "liveBroadcastContent": "live",
                    },
                    "liveStreamingDetails": {
                        "activeLiveChatId": "chat_xyz_789",
                        "concurrentViewers": "250",
                        "actualStartTime": "2026-08-16T12:00:00Z",
                    },
                }
            ]
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    creds = YouTubeCredentialManager(keys=["FakeKey1"])
    client = YouTubeAPIClient(credential_manager=creds, http_client=http_client)

    info = await client.get_live_stream_details("video_abc_123")
    assert info is not None
    assert info.stream_id == "video_abc_123"
    assert info.channel_id == "UC_channel_123"
    assert info.title == "Goddess AI Live Stream"
    assert info.status == StreamStatus.LIVE
    assert info.concurrent_viewers == 250
    assert info.live_chat_id == "chat_xyz_789"


@pytest.mark.asyncio
async def test_get_live_chat_messages_normalization():
    """Verify parsing of text and super chat events from mock response."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        data = {
            "pollingIntervalMillis": 3500,
            "nextPageToken": "token_page_2",
            "items": [
                {
                    "id": "msg_001",
                    "snippet": {
                        "type": "textMessageEvent",
                        "displayMessage": "Hello stream!",
                        "publishedAt": "2026-08-16T12:01:00Z",
                        "liveChatId": "chat_123",
                    },
                    "authorDetails": {
                        "channelId": "user_001",
                        "displayName": "ViewerOne",
                        "isChatOwner": False,
                        "isChatModerator": True,
                        "isChatSponsor": False,
                    },
                },
                {
                    "id": "msg_002",
                    "snippet": {
                        "type": "superChatEvent",
                        "publishedAt": "2026-08-16T12:01:05Z",
                        "liveChatId": "chat_123",
                        "superChatDetails": {
                            "amountDisplayString": "$10.00",
                            "userComment": "Keep up the great stream!",
                        },
                    },
                    "authorDetails": {
                        "channelId": "user_002",
                        "displayName": "SuperFan",
                        "isChatOwner": False,
                        "isChatModerator": False,
                        "isChatSponsor": True,
                    },
                },
            ],
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    creds = YouTubeCredentialManager(keys=["FakeKey1"])
    client = YouTubeAPIClient(credential_manager=creds, http_client=http_client)

    messages, next_token, interval = await client.get_live_chat_messages("chat_123")
    assert len(messages) == 2
    assert next_token == "token_page_2"
    assert interval == 3500

    # Verify standard message
    m1 = messages[0]
    assert m1.message_id == "msg_001"
    assert m1.message_text == "Hello stream!"
    assert m1.author_name == "ViewerOne"
    assert m1.is_chat_moderator is True
    assert m1.is_super_chat is False

    # Verify super chat
    m2 = messages[1]
    assert m2.message_id == "msg_002"
    assert m2.is_super_chat is True
    assert m2.super_chat_amount == "$10.00"
    assert m2.message_text == "Keep up the great stream!"
    assert m2.is_chat_sponsor is True


@pytest.mark.asyncio
async def test_quota_error_triggers_rotation():
    """Verify that HTTP 403 quota error triggers credential failover to next key."""
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        key = request.url.params.get("key")

        if key == "Key1":
            # Return quotaExceeded error on Key 1
            return httpx.Response(
                403,
                json={
                    "error": {
                        "message": "Quota exceeded",
                        "errors": [{"reason": "quotaExceeded"}],
                    }
                },
            )
        elif key == "Key2":
            # Succeed on Key 2
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "vid_1", "snippet": {"title": "Success Stream"}}]
                },
            )
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    creds = YouTubeCredentialManager(keys=["Key1", "Key2"])
    client = YouTubeAPIClient(credential_manager=creds, http_client=http_client)

    info = await client.get_live_stream_details("vid_1")
    assert info is not None
    assert info.title == "Success Stream"
    assert call_count == 2


@pytest.mark.asyncio
async def test_chat_message_validation():
    """Verify chat message length constraints."""
    creds = YouTubeCredentialManager(keys=["FakeKey1"])
    client = YouTubeAPIClient(credential_manager=creds)

    # Empty message
    with pytest.raises(ChatMessageValidationError):
        await client.send_chat_message("chat_123", "   ")

    # Message exceeding 200 characters
    long_text = "x" * 201
    with pytest.raises(ChatMessageValidationError):
        await client.send_chat_message("chat_123", long_text)
