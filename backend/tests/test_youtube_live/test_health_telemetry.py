"""
Tests for YouTube Live Health & Telemetry Reporting in GODDESS AI 2.0.
"""

from app.services.providers.health import ProviderHealthService
from app.services.youtube.stream_manager import StreamManager
from tests.test_youtube_live.fake_youtube_provider import FakeYouTubeProvider


def test_youtube_health_telemetry_aggregation():
    """Verify ProviderHealthService gathers safe live session and credential health metrics."""
    health = ProviderHealthService.get_youtube_provider_health()

    assert health.provider == "youtube"
    assert health.status in ("HEALTHY", "DEGRADED", "UNAVAILABLE", "NOT_CONFIGURED")
    assert isinstance(health.credentials, list)

    for cred in health.credentials:
        assert "raw_key" not in cred
        assert "api_key" not in cred
