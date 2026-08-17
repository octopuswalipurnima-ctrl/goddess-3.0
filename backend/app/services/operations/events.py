"""
Operational Event Publishing Subsystem for GODDESS AI 2.0.

Publishes structured operational events to the internal EventBus and WebSocket telemetry
stream with bounded memory and topic partitioning.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
import uuid

from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.operations.models import OperationalEvent, OperationalEventType

logger = get_logger("operations.events")

MAX_EVENT_HISTORY = 200


class OperationsEventPublisher:
    """Publishes operational state changes across EventBus and WebSocket subscriptions."""

    def __init__(self, max_history: int = MAX_EVENT_HISTORY):
        self._max_history = max_history
        self._event_history: Deque[OperationalEvent] = deque(maxlen=max_history)

    async def publish_event(
        self,
        event_type: OperationalEventType,
        payload: Dict[str, Any],
        stream_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> OperationalEvent:
        """
        Publish structured operational event onto EventBus and buffer in memory.
        """
        event = OperationalEvent(
            event_id=f"opev_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stream_id=stream_id,
            actor_id=actor_id,
            payload=payload,
        )

        self._event_history.append(event)

        # Publish to internal EventBus
        try:
            await event_bus.publish(event_type.value, event.model_dump())
            await event_bus.publish("OPERATIONAL_EVENT", event.model_dump())
        except Exception as exc:
            logger.warning(f"Failed to publish operational event on EventBus: {exc}")

        return event

    def get_recent_events(
        self,
        stream_id: Optional[str] = None,
        event_type: Optional[OperationalEventType] = None,
        limit: int = 50,
    ) -> List[OperationalEvent]:
        """Fetch recent bounded operational events."""
        bounded_limit = min(max(1, limit), 100)
        records = list(reversed(self._event_history))

        if stream_id:
            records = [r for r in records if r.stream_id in (stream_id, "GLOBAL", None)]
        if event_type:
            records = [r for r in records if r.event_type == event_type]

        return records[:bounded_limit]


# Global singleton instance
operations_event_publisher = OperationsEventPublisher()
