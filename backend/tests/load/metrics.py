"""
Load Testing Metrics Engine for GODDESS AI 2.0.

Collects high-resolution timing, throughput, queue depth, error rates, and failure events.
Computes standard statistical percentiles (p50, p95, p99) and produces machine-readable summaries.
"""

from dataclasses import dataclass, field
import statistics
import time
from typing import Any, Dict, List, Optional


@dataclass
class LoadMetrics:
    """Consolidated snapshot of load test execution metrics."""
    total_messages: int = 0
    processed_messages: int = 0
    dropped_messages: int = 0
    blocked_messages: int = 0
    moderation_actions: int = 0
    cohost_responses: int = 0
    command_requests: int = 0
    event_bus_events: int = 0
    errors: int = 0
    retries: int = 0
    failovers: int = 0
    
    # Latency percentiles in milliseconds
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    mean_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0

    # Rates & Capacities
    duration_seconds: float = 0.0
    throughput_msg_sec: float = 0.0
    error_rate: float = 0.0
    max_queue_depth: int = 0
    max_cache_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to clean dictionary format."""
        return {
            "total_messages": self.total_messages,
            "processed_messages": self.processed_messages,
            "dropped_messages": self.dropped_messages,
            "blocked_messages": self.blocked_messages,
            "moderation_actions": self.moderation_actions,
            "cohost_responses": self.cohost_responses,
            "command_requests": self.command_requests,
            "event_bus_events": self.event_bus_events,
            "errors": self.errors,
            "retries": self.retries,
            "failovers": self.failovers,
            "duration_seconds": round(self.duration_seconds, 3),
            "throughput_msg_sec": round(self.throughput_msg_sec, 2),
            "error_rate": round(self.error_rate, 4),
            "max_queue_depth": self.max_queue_depth,
            "max_cache_size": self.max_cache_size,
            "latency_ms": {
                "p50": round(self.p50_latency_ms, 2),
                "p95": round(self.p95_latency_ms, 2),
                "p99": round(self.p99_latency_ms, 2),
                "mean": round(self.mean_latency_ms, 2),
                "max": round(self.max_latency_ms, 2),
                "min": round(self.min_latency_ms, 2),
            },
        }

    def summary(self) -> str:
        """Format a human-readable text summary."""
        return (
            f"=== LOAD METRICS SUMMARY ===\n"
            f"Messages: {self.processed_messages}/{self.total_messages} processed ({self.blocked_messages} blocked, {self.dropped_messages} dropped)\n"
            f"Throughput: {self.throughput_msg_sec:.1f} msg/s (Duration: {self.duration_seconds:.2f}s)\n"
            f"Latency: p50={self.p50_latency_ms:.2f}ms | p95={self.p95_latency_ms:.2f}ms | p99={self.p99_latency_ms:.2f}ms\n"
            f"Actions: Moderation={self.moderation_actions}, CoHost={self.cohost_responses}, Commands={self.command_requests}\n"
            f"Failures: Errors={self.errors} (rate: {self.error_rate:.2%}), Retries={self.retries}, Failovers={self.failovers}\n"
            f"Capacity: Max Queue Depth={self.max_queue_depth}, Max Cache Size={self.max_cache_size}\n"
        )


class LoadMetricsCollector:
    """Thread-safe and async-safe collector for real-time load test metrics."""

    def __init__(self):
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.total_messages: int = 0
        self.processed_messages: int = 0
        self.dropped_messages: int = 0
        self.blocked_messages: int = 0
        self.moderation_actions: int = 0
        self.cohost_responses: int = 0
        self.command_requests: int = 0
        self.event_bus_events: int = 0
        self.errors: int = 0
        self.retries: int = 0
        self.failovers: int = 0
        
        self.latencies_ms: List[float] = []
        self.queue_depths: List[int] = []
        self.cache_sizes: List[int] = []

    def record_message_processed(self, latency_ms: float, blocked: bool = False, dropped: bool = False) -> None:
        self.total_messages += 1
        if dropped:
            self.dropped_messages += 1
        elif blocked:
            self.blocked_messages += 1
            self.processed_messages += 1
        else:
            self.processed_messages += 1

        self.latencies_ms.append(latency_ms)

    def record_moderation_action(self) -> None:
        self.moderation_actions += 1

    def record_cohost_response(self) -> None:
        self.cohost_responses += 1

    def record_command(self) -> None:
        self.command_requests += 1

    def record_event_bus(self, count: int = 1) -> None:
        self.event_bus_events += count

    def record_error(self) -> None:
        self.errors += 1

    def record_retry(self) -> None:
        self.retries += 1

    def record_failover(self) -> None:
        self.failovers += 1

    def record_queue_depth(self, depth: int) -> None:
        self.queue_depths.append(depth)

    def record_cache_size(self, size: int) -> None:
        self.cache_sizes.append(size)

    def finish(self) -> LoadMetrics:
        """Compute statistical percentiles and build the LoadMetrics snapshot."""
        self.end_time = time.time()
        duration = max(0.001, self.end_time - self.start_time)

        # Latency statistics
        if self.latencies_ms:
            sorted_latencies = sorted(self.latencies_ms)
            p50 = statistics.median(sorted_latencies)
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.99))]
            mean_lat = statistics.mean(sorted_latencies)
            max_lat = max(sorted_latencies)
            min_lat = min(sorted_latencies)
        else:
            p50 = p95 = p99 = mean_lat = max_lat = min_lat = 0.0

        throughput = self.processed_messages / duration
        error_rate = (self.errors / self.total_messages) if self.total_messages > 0 else 0.0
        max_q = max(self.queue_depths) if self.queue_depths else 0
        max_c = max(self.cache_sizes) if self.cache_sizes else 0

        return LoadMetrics(
            total_messages=self.total_messages,
            processed_messages=self.processed_messages,
            dropped_messages=self.dropped_messages,
            blocked_messages=self.blocked_messages,
            moderation_actions=self.moderation_actions,
            cohost_responses=self.cohost_responses,
            command_requests=self.command_requests,
            event_bus_events=self.event_bus_events,
            errors=self.errors,
            retries=self.retries,
            failovers=self.failovers,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            mean_latency_ms=mean_lat,
            max_latency_ms=max_lat,
            min_latency_ms=min_lat,
            duration_seconds=duration,
            throughput_msg_sec=throughput,
            error_rate=error_rate,
            max_queue_depth=max_q,
            max_cache_size=max_c,
        )
