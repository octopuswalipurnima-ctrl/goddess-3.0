"""
Tests for Safe Recovery Without Historical Replay in GODDESS AI 2.0.
"""

from app.services.youtube.stream_supervisor import StreamSupervisor


def test_supervisor_clean_recovery_on_startup():
    """Verify supervisor initializes with zero active sessions and does not replay historical state."""
    supervisor = StreamSupervisor(max_concurrent_streams=4)
    assert supervisor.active_stream_count == 0
    assert supervisor.total_stream_count == 0
    assert len(supervisor.list_supervisor_sessions()) == 0
