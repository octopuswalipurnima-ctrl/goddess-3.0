"""
Viewer Interaction Module for GODDESS AI 2.0.

Provides foundation for viewer interaction tracking (message count, first/last seen timestamps)
with bounded memory limits and strict isolation. No XP, levels, gambling, or monetization.
"""

from collections import OrderedDict
import time
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.models import ModuleCapability, ModuleMetadata
from app.services.youtube.models import ChatMessage

logger = get_logger("modules.viewer_interaction")


class ViewerRecord:
    """Bounded profile tracking viewer interaction count and timestamps."""

    def __init__(self, author_name: str):
        now = time.time()
        self.author_name: str = author_name
        self.message_count: int = 1
        self.first_seen: float = now
        self.last_seen: float = now

    def record_message(self, author_name: str) -> None:
        self.author_name = author_name
        self.message_count += 1
        self.last_seen = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "author_name": self.author_name,
            "message_count": self.message_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


class ViewerInteractionModule(BaseModule):
    """Tracks viewer chat participation counts and interaction timestamps."""

    def __init__(self, max_records_per_stream: int = 1000):
        metadata = ModuleMetadata(
            id="viewer_interaction",
            name="Viewer Interaction Tracker",
            version="1.0.0",
            description="Tracks chat participation frequency and active timestamps per viewer.",
            category="interaction",
            capabilities=[ModuleCapability.CHAT_READ],
            supported_events=["CHAT_MESSAGE"],
        )
        super().__init__(metadata)
        self.max_records = max_records_per_stream
        # stream_id -> OrderedDict of (author_id -> ViewerRecord)
        self._viewers: Dict[str, OrderedDict[str, ViewerRecord]] = {}

    def _get_stream_dict(self, stream_id: str) -> OrderedDict[str, ViewerRecord]:
        if stream_id not in self._viewers:
            self._viewers[stream_id] = OrderedDict()
        return self._viewers[stream_id]

    def get_viewer_stats(self, stream_id: str, author_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve interaction stats for a viewer."""
        stream_dict = self._get_stream_dict(stream_id)
        if author_id in stream_dict:
            return stream_dict[author_id].to_dict()
        return None

    def get_top_participants(self, stream_id: str, limit: int = 10) -> list[Dict[str, Any]]:
        """Retrieve most active viewers in stream."""
        stream_dict = self._get_stream_dict(stream_id)
        sorted_records = sorted(stream_dict.values(), key=lambda r: r.message_count, reverse=True)
        return [r.to_dict() for r in sorted_records[:limit]]

    async def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Process CHAT_MESSAGE to update viewer activity."""
        if event_name != "CHAT_MESSAGE":
            return

        try:
            msg = ChatMessage(**event_data)
        except Exception:
            return

        stream_id = msg.stream_id
        config = self.get_stream_config(stream_id)
        if not config.enabled:
            return

        stream_dict = self._get_stream_dict(stream_id)
        author_id = msg.author_id

        if author_id in stream_dict:
            record = stream_dict.pop(author_id)
            record.record_message(msg.author_name)
            stream_dict[author_id] = record  # Move to end (LRU)
        else:
            if len(stream_dict) >= self.max_records:
                stream_dict.popitem(last=False)
            stream_dict[author_id] = ViewerRecord(msg.author_name)
