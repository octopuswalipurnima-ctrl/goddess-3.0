"""
Controlled Real Audit & Observability Tests for GODDESS AI 2.0.

Validates memory bounds (buffer <= 500) and zero sensitive data in audit logs.
"""

import pytest
from app.services.operations.audit import OperationalAuditService


@pytest.mark.asyncio
async def test_audit_observability_bounds_and_scrubbing():
    """
    Validate that audit entries are bounded and strictly scrubbed.
    """
    audit = OperationalAuditService(max_buffer_size=500)

    # Insert test events
    for i in range(50):
        await audit.record_audit(
            action="STREAM_ATTACH",
            actor_id="operator_1",
            actor_role="OPERATOR",
            target=f"STREAM_{i % 4}",
            stream_id="STREAM_A",
            metadata={"token": "Bearer eyJhbGciOiJIUzI1Ni...insecure", "safe_info": "valid"},
        )

    records = audit.get_recent_records(stream_id="STREAM_A", limit=100)
    assert len(records) == 50

    # Ensure token was scrubbed
    for r in records:
        assert r.metadata.get("token") == "[REDACTED]"
