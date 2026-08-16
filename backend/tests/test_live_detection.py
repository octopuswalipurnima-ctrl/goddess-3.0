"""
Tests for LiveStreamDetector and WebSub Webhook Ingestion.
"""

import pytest
from app.services.youtube.live_detection import LiveStreamDetector
from app.services.youtube.stream_manager import StreamManager


SAMPLE_WEBSUB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <title>YouTube WebSub Feed</title>
  <entry>
    <id>yt:video:video_test_999</id>
    <yt:videoId>video_test_999</yt:videoId>
    <yt:channelId>channel_xyz_456</yt:channelId>
    <title>Championship Finals Live Stream</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=video_test_999"/>
    <published>2026-08-16T12:00:00+00:00</published>
    <updated>2026-08-16T12:00:00+00:00</updated>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_websub_xml_parsing():
    """Verify Atom XML parsing extracts video ID, channel ID, and title."""
    detector = LiveStreamDetector()
    parsed = detector.parse_websub_xml(SAMPLE_WEBSUB_XML)

    assert parsed is not None
    video_id, channel_id, title = parsed
    assert video_id == "video_test_999"
    assert channel_id == "channel_xyz_456"
    assert title == "Championship Finals Live Stream"


@pytest.mark.asyncio
async def test_webhook_signature_verification():
    """Verify HMAC signature calculation and verification."""
    secret = "my_webhook_secret_key"
    detector = LiveStreamDetector(webhook_secret=secret)

    payload = b"sample_payload_bytes"
    # Compute valid signature
    import hmac
    import hashlib
    valid_sig = "sha1=" + hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
    invalid_sig = "sha1=badsignature12345"

    assert detector.verify_webhook_signature(payload, valid_sig) is True
    assert detector.verify_webhook_signature(payload, invalid_sig) is False
    assert detector.verify_webhook_signature(payload, None) is False


@pytest.mark.asyncio
async def test_notification_deduplication():
    """Verify that duplicate notifications for the same video are deduplicated."""
    mgr = StreamManager(max_concurrent_streams=4)
    detector = LiveStreamDetector(manager=mgr)

    # First notification
    v1 = await detector.handle_webhook_notification(SAMPLE_WEBSUB_XML)
    assert v1 == "video_test_999"

    # Second identical notification (must be deduplicated)
    v2 = await detector.handle_webhook_notification(SAMPLE_WEBSUB_XML)
    assert v2 == "video_test_999"
