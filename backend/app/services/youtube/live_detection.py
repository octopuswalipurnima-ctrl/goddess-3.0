"""
Live Stream Detection & WebSub Webhook Ingestion Service for GODDESS AI 2.0.

Processes YouTube WebSub (PubSubHubbub) push notifications and manages fallback
controlled channel live stream detection.
"""

import hmac
import hashlib
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Set
from collections import OrderedDict
import time

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.youtube.client import YouTubeAPIClient, youtube_client
from app.services.youtube.stream_manager import StreamManager, stream_manager

logger = get_logger("youtube.detection")

# XML Namespaces used in YouTube WebSub Atom feeds
ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


class LiveStreamDetector:
    """Handles WebSub notifications and live stream discovery."""

    def __init__(
        self,
        manager: Optional[StreamManager] = None,
        api_client: Optional[YouTubeAPIClient] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.manager = manager or stream_manager
        self.client = api_client or youtube_client
        self.webhook_secret = webhook_secret

        # Deduplication cache for notification video IDs
        self._processed_notifications: OrderedDict[str, float] = OrderedDict()
        self._max_cache = 1000

    def verify_webhook_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Verify HMAC-SHA1 signature if a webhook secret is configured.
        Format: sha1=<hex_digest>
        """
        if not self.webhook_secret:
            return True  # If no secret configured, allow payload

        if not signature_header or not signature_header.startswith("sha1="):
            logger.warning("Missing or invalid X-Hub-Signature header format.")
            return False

        expected_sig = signature_header.split("sha1=")[1]
        computed_sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha1,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, computed_sig)

    def parse_websub_xml(self, xml_content: str) -> Optional[Tuple[str, str, str]]:
        """
        Parses YouTube WebSub XML feed.
        Returns tuple of (video_id, channel_id, title) if found, else None.
        """
        try:
            root = ET.fromstring(xml_content)
            entry = root.find("atom:entry", ATOM_NS)
            if entry is None:
                # Also try without namespace prefix in case of raw XML
                entry = root.find("entry")
                if entry is None:
                    return None

            video_id_elem = entry.find("yt:videoId", ATOM_NS)
            if video_id_elem is None:
                video_id_elem = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")

            channel_id_elem = entry.find("yt:channelId", ATOM_NS)
            if channel_id_elem is None:
                channel_id_elem = entry.find("{http://www.youtube.com/xml/schemas/2015}channelId")

            title_elem = entry.find("atom:title", ATOM_NS)
            if title_elem is None:
                title_elem = entry.find("title")

            video_id = video_id_elem.text.strip() if video_id_elem is not None and video_id_elem.text else ""
            channel_id = channel_id_elem.text.strip() if channel_id_elem is not None and channel_id_elem.text else ""
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled Stream"

            if video_id:
                return video_id, channel_id, title
            return None

        except ET.ParseError as e:
            logger.error(f"Failed to parse WebSub XML notification: {e}")
            return None

    async def handle_webhook_notification(self, raw_xml: str, signature_header: Optional[str] = None) -> Optional[str]:
        """
        Process incoming WebSub webhook push notification.
        Extracts stream ID, validates uniqueness, and creates stream session.
        """
        if not self.verify_webhook_signature(raw_xml.encode("utf-8"), signature_header):
            logger.warning("Rejecting WebSub notification with invalid signature.")
            return None

        parsed = self.parse_websub_xml(raw_xml)
        if not parsed:
            logger.debug("WebSub notification contained no video entry.")
            return None

        video_id, channel_id, title = parsed

        # Deduplication check
        if video_id in self._processed_notifications:
            logger.debug(f"Ignoring duplicate notification for video '{video_id}'")
            return video_id

        self._processed_notifications[video_id] = time.time()
        if len(self._processed_notifications) > self._max_cache:
            self._processed_notifications.popitem(last=False)

        logger.info(f"Detected YouTube video/stream from WebSub: '{video_id}' ({title})")

        await event_bus.publish(
            "STREAM_DETECTED",
            {
                "stream_id": video_id,
                "channel_id": channel_id,
                "title": title,
                "source": "websub",
            },
        )

        # Attempt to auto-create and start session if live
        try:
            await self.manager.create_session(video_id, channel_id=channel_id, auto_start=True)
        except Exception as e:
            logger.warning(f"Could not automatically start session for '{video_id}': {e}")

        return video_id


# Global singleton instance of LiveStreamDetector
live_detector = LiveStreamDetector()
