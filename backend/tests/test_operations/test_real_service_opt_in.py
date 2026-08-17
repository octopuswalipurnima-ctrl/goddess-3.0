"""
Tests for Real-Service Opt-In Guardrails in GODDESS AI 2.0.
"""

import os
import pytest


def test_real_service_opt_in_defaults_to_false():
    """Verify all real service tests require explicit opt-in environment variables."""
    run_yt = os.getenv("RUN_REAL_YOUTUBE_TEST", "false").lower() == "true"
    run_gemini = os.getenv("RUN_REAL_GEMINI_TEST", "false").lower() == "true"
    run_postgres = os.getenv("RUN_REAL_POSTGRES_TEST", "false").lower() == "true"
    run_redis = os.getenv("RUN_REAL_REDIS_TEST", "false").lower() == "true"

    assert run_yt is False
    assert run_gemini is False
    assert run_postgres is False
    assert run_redis is False
