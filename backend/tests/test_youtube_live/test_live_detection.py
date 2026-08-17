"""
Tests for YouTube WebSub Live Stream Discovery in GODDESS AI 2.0.
"""

from app.services.youtube.live_detection import LiveStreamDetector
from app.services.youtube.stream_manager import StreamManager
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


def test_websub_xml_parsing_standard_atom():
    """Verify parsing valid YouTube WebSub XML feed returns video_id, channel_id, and title."""
    detector = LiveStreamDetector()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
        <entry>
            <yt:videoId>v_live_998877</yt:videoId>
            <yt:channelId>UC_test_channel_123</yt:channelId>
            <title>Awesome 24/7 Stream</title>
        </entry>
    </feed>
    """
    parsed = detector.parse_websub_xml(xml_content)
    assert parsed is not None
    video_id, channel_id, title = parsed
    assert video_id == "v_live_998877"
    assert channel_id == "UC_test_channel_123"
    assert title == "Awesome 24/7 Stream"


def test_websub_hmac_signature_verification():
    """Verify HMAC SHA1 signature verification against configured webhook secret."""
    detector = LiveStreamDetector(webhook_secret="super_secret_webhook_key")
    payload = b"<feed>sample</feed>"

    import hashlib
    import hmac
    expected_hex = hmac.new(b"super_secret_webhook_key", payload, hashlib.sha1).hexdigest()
    valid_header = f"sha1={expected_hex}"

    assert detector.verify_webhook_signature(payload, valid_header) is True
    assert detector.verify_webhook_signature(payload, "sha1=invalid_hex_signature") is False
    assert detector.verify_webhook_signature(payload, None) is False
