"""
Tests for Per-Stream AI Intelligence Configuration Isolation in GODDESS AI 2.0.
"""

from app.services.ai.decision_engine import AIDecisionEngine


def test_ai_config_per_stream_isolation():
    """Verify modifying AIConfig for STREAM_A does not alter STREAM_B, C, or D configs."""
    engine = AIDecisionEngine()

    # Configure Stream A
    engine.update_stream_config(
        "STREAM_A",
        {
            "enabled": True,
            "dry_run": True,
            "cooldown_seconds": 12.0,
            "confidence_threshold": 0.95,
        },
    )

    # Configure Stream B
    engine.update_stream_config(
        "STREAM_B",
        {
            "enabled": False,
            "dry_run": False,
            "cooldown_seconds": 2.0,
            "confidence_threshold": 0.50,
        },
    )

    cfg_a = engine.get_stream_config("STREAM_A")
    cfg_b = engine.get_stream_config("STREAM_B")
    cfg_c = engine.get_stream_config("STREAM_C")  # Default

    assert cfg_a.dry_run is True
    assert cfg_a.cooldown_seconds == 12.0
    assert cfg_a.confidence_threshold == 0.95

    assert cfg_b.enabled is False
    assert cfg_b.dry_run is False
    assert cfg_b.cooldown_seconds == 2.0
    assert cfg_b.confidence_threshold == 0.50

    # Stream C remains default
    assert cfg_c.enabled is True
    assert cfg_c.dry_run is False
    assert cfg_c.cooldown_seconds == 5.0
