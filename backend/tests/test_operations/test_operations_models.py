"""
Tests for Operations Domain Models and Schemas in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.models import (
    AIHealth,
    AuditEvent,
    ComponentStatus,
    InfrastructureHealth,
    LatencyMetrics,
    OperationalEvent,
    OperationalEventType,
    ProviderOperations,
    SafeCredentialSummary,
    StreamOperations,
    SystemHealthDetailed,
    SystemOverview,
)


def test_operations_models_instantiation_and_defaults():
    """Verify default instantiation of all operational models."""
    sys_ov = SystemOverview()
    assert sys_ov.system_status == ComponentStatus.HEALTHY
    assert sys_ov.production_mode == "PRODUCTION_SAFE"

    ai_h = AIHealth()
    assert ai_h.provider_status == ComponentStatus.HEALTHY
    assert ai_h.queue_depth == 0

    prov = ProviderOperations(provider_name="YouTube")
    assert prov.provider_name == "YouTube"
    assert prov.healthy_keys == 0

    st_ops = StreamOperations(stream_id="STREAM_A")
    assert st_ops.stream_id == "STREAM_A"
    assert st_ops.status == "OFFLINE"

    aud = AuditEvent(action="TEST_ACTION")
    assert aud.action == "TEST_ACTION"
    assert aud.audit_id.startswith("aud_")
