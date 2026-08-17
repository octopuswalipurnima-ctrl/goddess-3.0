"""
Tests for AI Co-Host Fail-Closed and Response Capping in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.manager import cohost_manager


def test_cohost_length_and_policy_bounds():
    """Verify co-host config and bounded lengths."""
    cfg = cohost_manager.get_config("STREAM_A")
    assert cfg is not None
    assert cfg.max_response_length <= 500
