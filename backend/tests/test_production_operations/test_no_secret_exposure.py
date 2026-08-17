"""
Tests for Zero Secret Exposure in Operations Layer in GODDESS AI 2.0.
"""

from app.core.production_health import ProductionHealthService
from app.core.safety_controller import safety_controller
from app.services.youtube.stream_supervisor import StreamSupervisorSession


def test_zero_secret_in_supervisor_summary():
    """Verify StreamSupervisorSummary model has no secret or credential fields."""
    session = StreamSupervisorSession("STREAM_SECRET_TEST")
    summary = session.to_summary()
    dumped = summary.model_dump()

    for key in ["api_key", "secret", "token", "password", "authorization"]:
        assert key not in dumped


def test_zero_secret_in_production_health():
    """Verify SystemProductionHealth model contains no credentials."""
    health = ProductionHealthService.get_system_production_health()
    dumped = health.model_dump()

    text_repr = str(dumped)
    assert "AIzaSy" not in text_repr
    assert "Bearer" not in text_repr
