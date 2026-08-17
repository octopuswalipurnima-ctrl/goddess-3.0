"""
Simulation Scenarios for Multi-Stream Load Testing.

Defines deterministic test parameters for 4-stream standard load, burst spikes,
moderation stress, and emergency stop scenarios.
"""

from dataclasses import dataclass, field
from typing import List

from tests.load.traffic import TrafficProfile


@dataclass
class LoadScenario:
    """Configuration for a deterministic multi-stream simulation scenario."""
    name: str
    stream_ids: List[str] = field(default_factory=lambda: ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"])
    viewers_per_stream: int = 200
    messages_per_stream: int = 250
    profile: TrafficProfile = TrafficProfile.MIXED
    target_rate_msg_s: float = 100.0
    random_seed: int = 42

    @property
    def total_viewers(self) -> int:
        return len(self.stream_ids) * self.viewers_per_stream

    @property
    def total_messages(self) -> int:
        return len(self.stream_ids) * self.messages_per_stream


def Standard4StreamScenario(messages_per_stream: int = 250) -> LoadScenario:
    """Standard 4-stream scenario with 200 viewers per stream (800 total viewers)."""
    return LoadScenario(
        name="Standard-4-Stream-800-Viewers",
        stream_ids=["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"],
        viewers_per_stream=200,
        messages_per_stream=messages_per_stream,
        profile=TrafficProfile.MIXED,
        target_rate_msg_s=250.0,
        random_seed=42,
    )


def Burst4StreamScenario(messages_per_stream: int = 150) -> LoadScenario:
    """Burst scenario simulating traffic spikes across all 4 streams."""
    return LoadScenario(
        name="Burst-4-Stream-Spike",
        stream_ids=["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"],
        viewers_per_stream=200,
        messages_per_stream=messages_per_stream,
        profile=TrafficProfile.BURST,
        target_rate_msg_s=500.0,
        random_seed=99,
    )


def ModerationHeavyScenario(messages_per_stream: int = 200) -> LoadScenario:
    """Moderation-heavy scenario with high spam and rule violations."""
    return LoadScenario(
        name="Moderation-Heavy-Stress",
        stream_ids=["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"],
        viewers_per_stream=200,
        messages_per_stream=messages_per_stream,
        profile=TrafficProfile.MODERATION_HEAVY,
        target_rate_msg_s=200.0,
        random_seed=123,
    )
