"""
Stream Awareness Engine for AI Co-Host in GODDESS AI 2.0.
Provides bounded, stream-scoped metadata and real-time activity context.
"""

from typing import Any, Dict, List, Optional
from app.core.logging import get_logger
from app.services.cohost.models import StreamAwarenessData

logger = get_logger("cohost.awareness")


class StreamAwarenessEngine:
    """Provides stream-scoped context including current activity, stream status, and recent events."""

    def __init__(self):
        # stream_id -> StreamAwarenessData
        self._awareness_data: Dict[str, StreamAwarenessData] = {}

    def get_awareness(self, stream_id: str) -> StreamAwarenessData:
        """Get or initialize awareness metadata for a specific stream."""
        if stream_id not in self._awareness_data:
            self._awareness_data[stream_id] = StreamAwarenessData(stream_id=stream_id)
        return self._awareness_data[stream_id]

    def update_awareness(self, stream_id: str, updates: Dict[str, Any]) -> StreamAwarenessData:
        """Update stream awareness state."""
        current = self.get_awareness(stream_id)
        data = current.model_dump()
        data.update(updates)
        data["stream_id"] = stream_id
        updated = StreamAwarenessData(**data)
        self._awareness_data[stream_id] = updated
        logger.info(f"Updated stream awareness for '{stream_id}': Activity='{updated.current_activity}'")
        return updated

    def set_activity(self, stream_id: str, activity: str, category: str = "Gaming") -> StreamAwarenessData:
        """Convenience method to update stream activity and category."""
        return self.update_awareness(stream_id, {"current_activity": activity, "category": category})

    def record_moderation_event(self, stream_id: str, event_summary: str) -> None:
        """Record a bounded recent moderation event (max 5 items)."""
        aw = self.get_awareness(stream_id)
        aw.recent_moderation_events.append(event_summary)
        if len(aw.recent_moderation_events) > 5:
            aw.recent_moderation_events = aw.recent_moderation_events[-5:]

    def clear_stream_awareness(self, stream_id: str) -> None:
        """Clear awareness data when a stream terminates."""
        if stream_id in self._awareness_data:
            del self._awareness_data[stream_id]
            logger.info(f"Cleared stream awareness for '{stream_id}'.")

    def build_awareness_prompt(self, stream_id: str) -> str:
        """Format stream awareness metadata into a safe, bounded prompt block."""
        aw = self.get_awareness(stream_id)
        lines = [
            "=== CURRENT STREAM STATUS & AWARENESS ===",
            f"- Stream State: {aw.stream_status}",
            f"- Current Activity: {aw.current_activity} ({aw.category})",
        ]

        if aw.custom_facts:
            lines.append("- Creator Quick Facts:")
            for k, v in list(aw.custom_facts.items())[:5]:
                lines.append(f"  * {k}: {v}")

        if aw.recent_moderation_events:
            lines.append("- Recent Stream Events (FYI only):")
            for ev in aw.recent_moderation_events[-3:]:
                lines.append(f"  * {ev}")

        return "\n".join(lines)


# Global singleton instance
stream_awareness_engine = StreamAwarenessEngine()
