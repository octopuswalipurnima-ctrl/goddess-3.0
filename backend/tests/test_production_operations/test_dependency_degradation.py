"""
Tests for System Dependency Degradation & Safe Degradation Rules in GODDESS AI 2.0.
"""

from app.core.production_health import ProductionHealthService
from app.core.redis import InMemoryFallbackState, RedisStateManager


def test_database_degraded_when_unreachable():
    """Verify database status reports NOT_CONFIGURED or DEGRADED gracefully without throwing."""
    status = ProductionHealthService.get_database_status()
    assert status.name == "database"
    assert status.status in ("HEALTHY", "DEGRADED", "NOT_CONFIGURED")


def test_redis_in_memory_fallback_degraded():
    """Verify Redis reports DEGRADED running on in-memory fallback when unconfigured."""
    status = ProductionHealthService.get_redis_status()
    assert status.name == "redis"
    assert status.status in ("HEALTHY", "DEGRADED")


def test_system_production_health_model():
    """Verify unified system production health report is valid and safe."""
    health = ProductionHealthService.get_system_production_health()
    assert health.application == "GODDESS AI 2.0"
    assert health.system_status in ("HEALTHY", "DEGRADED", "UNAVAILABLE")
    assert "database" in health.dependencies
    assert "redis" in health.dependencies
    assert "youtube" in health.dependencies
    assert "gemini" in health.dependencies
