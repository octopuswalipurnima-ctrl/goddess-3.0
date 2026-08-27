"""Tests for WebSub hub challenge verification and XML feed parsing."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.workers import parse_websub_xml_feed

SAMPLE_ATOM_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <link rel="hub" href="https://pubsubhubbub.appspot.com"/>
  <link rel="self" href="https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC_SAMPLE_123"/>
  <title>YouTube video feed</title>
  <updated>2026-08-26T14:30:00+00:00</updated>
  <entry>
    <id>yt:video:VIDEO_XYZ_999</id>
    <yt:videoId>VIDEO_XYZ_999</yt:videoId>
    <yt:channelId>UC_SAMPLE_123</yt:channelId>
    <title>Goddess AI 3.0 Live Stream</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=VIDEO_XYZ_999"/>
    <author>
      <name>Streamer Name</name>
      <uri>https://www.youtube.com/channel/UC_SAMPLE_123</uri>
    </author>
    <published>2026-08-26T14:30:00+00:00</published>
    <updated>2026-08-26T14:30:00+00:00</updated>
  </entry>
</feed>
"""


def test_parse_websub_xml_feed():
    """Test XML parsing of YouTube Atom feed."""
    channel_id, video_id = parse_websub_xml_feed(SAMPLE_ATOM_FEED)
    assert channel_id == "UC_SAMPLE_123"
    assert video_id == "VIDEO_XYZ_999"


@pytest.mark.asyncio
async def test_websub_get_verification_endpoint():
    """Test GET /websub/youtube challenge echo."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            "/websub/youtube",
            params={
                "hub.mode": "subscribe",
                "hub.topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC123",
                "hub.challenge": "challenge_token_abc_123",
                "hub.lease_seconds": 864000,
            },
        )
        assert resp.status_code == 200
        assert resp.text == "challenge_token_abc_123"


@pytest.mark.asyncio
async def test_health_live_endpoint():
    """Test ultra-lightweight GET /health/live endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "live"}


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test GET /health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "database" in data
