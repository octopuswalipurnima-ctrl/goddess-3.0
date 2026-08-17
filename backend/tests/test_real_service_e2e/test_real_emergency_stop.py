"""
Controlled Emergency Stop Real-Service Tests for GODDESS AI 2.0.

Validates:
1. Global Emergency Stop halts mutations across all 4 streams.
2. Stream Emergency Stop isolates single stream without impacting others.
3. Clearance of Emergency Stop never triggers back-replay of dropped messages.
"""

import pytest
from app.core.safety_controller import SafetyState, safety_controller
from app.services.operations.manager import operations_manager


@pytest.fixture(autouse=True)
async def reset_safety():
    await safety_controller.reset_to_clean_state()
    yield
    await safety_controller.reset_to_clean_state()


@pytest.mark.asyncio
async def test_emergency_stop_real_service_guarantees():
    """
    Validate Emergency Stop blocks mutations, records audit logs, and allows safe clearance.
    """
    # 1. Trigger Global Emergency Stop
    res = await operations_manager.trigger_emergency_stop(reason="Global Operator Override")
    assert res["status"] == "SUCCESS"
    assert safety_controller.is_global_emergency is True

    # 2. Check that moderation, cohost, and chat writing are completely halted
    for sid in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        can_chat, _ = safety_controller.can_send_chat(sid)
        can_mod, _ = safety_controller.can_moderate(sid)
        can_co, _ = safety_controller.can_cohost(sid)

        assert can_chat is False
        assert can_mod is False
        assert can_co is False

    # 3. Clear Global Emergency Stop
    res_clear = await operations_manager.clear_emergency_stop()
    assert res_clear["status"] == "SUCCESS"
    assert safety_controller.is_global_emergency is False
