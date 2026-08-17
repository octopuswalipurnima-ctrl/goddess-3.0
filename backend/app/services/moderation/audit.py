"""
Moderation Audit Logger and Real-Time Event Dispatcher.

Maintains bounded in-memory audit logs per stream, publishes lifecycle events
to the Event Bus, and broadcasts live feeds to connected WebSocket dashboards.
"""

from collections import deque
from typing import Deque, Dict, List, Optional

from app.api.v1.endpoints.ws import ws_manager
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.moderation.models import (
    ActionStatus,
    ModerationAction,
    ModerationAuditRecord,
    ModerationDecision,
)

logger = get_logger("moderation.audit")


class ModerationAuditLogger:
    """Records audit logs and dispatches real-time moderation events."""

    def __init__(self, max_records_per_stream: int = 1000):
        self.max_records_per_stream = max_records_per_stream
        # stream_id -> deque of ModerationAuditRecord
        self._audit_logs: Dict[str, Deque[ModerationAuditRecord]] = {}

    def _get_stream_log(self, stream_id: str) -> Deque[ModerationAuditRecord]:
        if stream_id not in self._audit_logs:
            self._audit_logs[stream_id] = deque(maxlen=self.max_records_per_stream)
        return self._audit_logs[stream_id]

    async def record_audit(
        self,
        decision: ModerationDecision,
        action_taken: ModerationAction,
        action_status: ActionStatus,
        block_reason: Optional[str] = None,
    ) -> ModerationAuditRecord:
        """
        Create audit record, store in ring buffer, and dispatch events.
        """
        stream_id = decision.stream_id
        idempotency_key = f"{stream_id}:{decision.message_id}:{action_taken.value}"

        record = ModerationAuditRecord(
            stream_id=stream_id,
            message_id=decision.message_id,
            author_id=decision.author_id,
            author_name=decision.author_name,
            decision=decision,
            action_taken=action_taken,
            action_status=action_status,
            block_reason=block_reason,
            idempotency_key=idempotency_key,
        )

        stream_log = self._get_stream_log(stream_id)
        stream_log.append(record)

        # Publish specific lifecycle events to internal Event Bus
        if action_status == ActionStatus.EXECUTED:
            await event_bus.publish("MODERATION_ACTION_EXECUTED", record.model_dump())
        elif action_status == ActionStatus.BLOCKED:
            await event_bus.publish("MODERATION_ACTION_BLOCKED", record.model_dump())
        elif action_status == ActionStatus.FAILED:
            await event_bus.publish("MODERATION_ACTION_FAILED", record.model_dump())

        # Broadcast live audit payload to dashboard WebSockets
        await ws_manager.broadcast_json({
            "type": "MODERATION_EVENT",
            "data": record.model_dump(),
        })

        return record

    def get_recent_records(
        self, stream_id: str, limit: int = 50
    ) -> List[ModerationAuditRecord]:
        """Fetch latest audit records for a stream."""
        if stream_id not in self._audit_logs:
            return []
        log_items = list(self._audit_logs[stream_id])
        return log_items[-limit:]


# Global singleton instance of ModerationAuditLogger
moderation_audit_logger = ModerationAuditLogger()
