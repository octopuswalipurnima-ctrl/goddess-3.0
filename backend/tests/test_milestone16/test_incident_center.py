"""
Tests for Incident Center Event Formats in GODDESS AI 2.0.
"""

from datetime import datetime, timezone
import pytest
from app.services.operations.models import OperationalEvent


def test_incident_operational_event_schema():
    """Verify operational incident event model serialization."""
    event = OperationalEvent(
        event_type="EMERGENCY_STOP",
        stream_id="STREAM_A",
        actor_id="operator_1",
        payload={"reason": "Manual Stop Triggered"},
    )

    assert event.event_id is not None
    assert event.event_type == "EMERGENCY_STOP"
    assert event.stream_id == "STREAM_A"
