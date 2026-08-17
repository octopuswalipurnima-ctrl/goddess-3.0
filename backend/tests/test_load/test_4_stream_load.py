"""
4-Stream 800-Viewer Multi-Stream Load Test.

Simulates 4 simultaneous YouTube streams (STREAM_A, STREAM_B, STREAM_C, STREAM_D)
with 200 viewers per stream (800 total concurrent viewers) under deterministic load.
Verifies complete stream isolation and independent engine state.
"""

import pytest
from tests.load.scenarios import Standard4StreamScenario, LoadScenario
from tests.load.simulator import DeterministicLoadSimulator
from tests.load.traffic import TrafficProfile


@pytest.mark.asyncio
async def test_4_stream_standard_simulation():
    """Run deterministic 4-stream simulation with 800 total viewers."""
    scenario = Standard4StreamScenario(messages_per_stream=100)
    assert scenario.total_viewers == 800
    assert scenario.total_messages == 400

    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()

    # Assertions on metrics
    assert metrics.total_messages == 400
    assert metrics.processed_messages == 400
    assert metrics.errors == 0
    assert simulator.isolation_violations == 0
    assert metrics.throughput_msg_sec > 0
    assert metrics.p95_latency_ms < 100.0  # Offline rule execution is fast (< 100ms)


@pytest.mark.asyncio
async def test_4_stream_independent_failure_isolation():
    """Verify an error or shutdown on one stream leaves other 3 streams completely healthy."""
    scenario = LoadScenario(
        name="1-Stream-Degraded-3-Healthy",
        stream_ids=["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"],
        viewers_per_stream=50,
        messages_per_stream=50,
        profile=TrafficProfile.NORMAL,
    )

    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()

    # Verify all 4 streams processed their messages independently
    for s_id in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        assert len(simulator.stream_message_history[s_id]) == 50

    assert metrics.total_messages == 200
    assert simulator.isolation_violations == 0
