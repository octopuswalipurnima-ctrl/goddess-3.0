"""
Tests for Centralized Version and Build Information in GODDESS AI 2.0.
"""

import pytest
from app.core.version import APP_VERSION, get_version_info


def test_version_info_structure():
    """Verify version info schema and values."""
    info = get_version_info()
    assert info["version"] == APP_VERSION
    assert "release_milestone" in info
    assert "git_commit" in info
    assert info["production_ready"] is True
