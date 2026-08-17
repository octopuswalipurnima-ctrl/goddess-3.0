"""
Tests for 4-Stream Operations across STREAM_A, STREAM_B, STREAM_C, and STREAM_D.
"""

import pytest
from app.services.operations.manager import OperationsManager


def test_four_stream_operations_summary_coverage():
    """Verify operational overview includes all four primary streams."""
    mgr = OperationsManager()
    all_streams = mgr.get_all_stream_operations()

    for sid in ["STREAM_A", "STREAM_B", "STREAM_C", "STREAM_D"]:
        assert sid in all_streams
        assert all_streams[sid].stream_id == sid
