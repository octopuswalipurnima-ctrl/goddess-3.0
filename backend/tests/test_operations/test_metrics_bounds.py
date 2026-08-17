"""
Tests for Metrics Memory Bounds in GODDESS AI 2.0.
"""

import pytest
from app.services.operations.telemetry import PercentileTracker


def test_percentile_tracker_bounds_memory_samples():
    """Verify PercentileTracker enforces max_samples bound to avoid memory leaks."""
    tracker = PercentileTracker(max_samples=100)

    for i in range(500):
        tracker.record(float(i))

    metrics = tracker.calculate()
    assert metrics.sample_count == 100
    assert len(tracker._samples) == 100
