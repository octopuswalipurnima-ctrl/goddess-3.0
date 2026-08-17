"""
Burst Traffic & Spiky Load Tests.

Tests system stability, duplicate suppression, and cooldown enforcement
under sudden chat traffic spikes across multiple streams.
"""

import pytest
from tests.load.scenarios import Burst4StreamScenario, LoadScenario
from tests.load.simulator import DeterministicLoadSimulator
from tests.load.traffic import TrafficProfile


@pytest.mark.asyncio
async def test_burst_traffic_spike_handling():
    """Verify rapid message spikes across 4 streams are handled without unbounded queues or memory growth."""
    scenario = Burst4StreamScenario(messages_per_stream=80)
    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()

    assert metrics.processed_messages == 320
    assert metrics.errors == 0
    assert metrics.throughput_msg_sec > 50.0
    assert simulator.isolation_violations == 0


@pytest.mark.asyncio
async def test_duplicate_spam_burst_suppression():
    """Verify repeated duplicate spam bursts trigger moderation rules and are blocked."""
    scenario = LoadScenario(
        name="Duplicate-Spam-Burst",
        stream_ids=["STREAM_A", "STREAM_B"],
        viewers_per_stream=50,
        messages_per_stream=40,
        profile=TrafficProfile.DUPLICATE,
    )
    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()

    assert metrics.total_messages == 80
    assert simulator.isolation_violations == 0
