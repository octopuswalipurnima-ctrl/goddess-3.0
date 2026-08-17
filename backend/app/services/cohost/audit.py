"""
Audit Logger and WebSocket Dispatcher for AI Co-Host in GODDESS AI 2.0.

Maintains bounded in-memory circular logs (max 1,000 records per stream)
and broadcasts real-time telemetry to the Creator Dashboard.
"""

from collections import deque
from typing import Deque, Dict, List, Optional

from app.api.v1.endpoints.ws import ws_manager
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.cohost.models import CoHostAuditRecord

logger = get_logger("cohost.audit")


class CoHostAuditLogger:
    """Manages audit records and real-time dashboard events for Co-Host interactions."""

    def __init__(self, max_records_per_stream: int = 1000):
        self.max_records = max_records_per_stream
        # stream_id -> deque of CoHostAuditRecord
        self._records: Dict[str, Deque[CoHostAuditRecord]] = {}

    def get_recent_records(self, stream_id: str, limit: int = 50) -> List[CoHostAuditRecord]:
        """Fetch the most recent audit records for a stream."""
        if stream_id not in self._records:
            return []
        records = list(self._records[stream_id])
        return records[-limit:]

    async def record_audit(self, record: CoHostAuditRecord) -> None:
        """
        Record a Co-Host interaction in the circular log, publish to Event Bus,
        and broadcast to connected dashboard WebSockets.
        """
        stream_id = record.stream_id
        if stream_id not in self._records:
            self._records[stream_id] = deque(maxlen=self.max_records)

        self._records[stream_id].append(record)

        # 1. Publish to internal Event Bus
        event_name = f"COHOST_RESPONSE_{record.response_status.value}"
        await event_bus.publish(event_name, record.model_dump())

        # 2. Broadcast to real-time WebSockets
        try:
            await ws_manager.broadcast_json({
                "type": "COHOST_EVENT",
                "stream_id": stream_id,
                "data": record.model_dump(),
            })
        except Exception as exc:
            logger.debug(f"Failed to broadcast Co-Host WebSocket event: {exc}")


# Global singleton audit logger
cohost_audit_logger = CoHostAuditLogger()
