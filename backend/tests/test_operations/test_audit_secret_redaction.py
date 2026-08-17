"""
Tests for Zero Secret Redaction in Audit Logs in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.audit import OperationalAuditService


@pytest.mark.asyncio
async def test_audit_log_scrubs_raw_credentials_and_headers():
    """Verify raw API keys and Bearer tokens are scrubbed from reason and metadata."""
    audit = OperationalAuditService()

    event = await audit.record_audit(
        action="CONFIG_CHANGE",
        actor_id="admin_1",
        reason="Updated key to AIzaSyDummyRawKey123456789012345678901234",
        metadata={
            "auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
            "api_key": "AIzaSyDummyRawKey123456789012345678901234",
            "safe_note": "Normal configuration update",
        },
    )

    assert "AIzaSyDummyRawKey123456789012345678901234" not in (event.reason or "")
    assert "[REDACTED_CREDENTIAL]" in (event.reason or "")
    assert event.metadata["api_key"] == "[REDACTED]"
