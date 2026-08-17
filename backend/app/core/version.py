"""
Centralized Version and Build Information for GODDESS AI 2.0.

Provides immutable build metadata, release versioning, and environment mode
without exposing internal paths, secrets, or raw host identifiers.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict

APP_VERSION = "2.0.0"
RELEASE_MILESTONE = "Milestone 16 (Production Launch & Autonomous Reliability)"
BUILD_TIMESTAMP = "2026-08-18T00:00:00Z"
GIT_COMMIT = "7b20c96"


def get_version_info() -> Dict[str, Any]:
    """
    Return safe build and version metadata for health probes and dashboards.
    """
    return {
        "app_name": "GODDESS AI",
        "version": APP_VERSION,
        "release_milestone": RELEASE_MILESTONE,
        "git_commit": os.getenv("RAILWAY_GIT_COMMIT_SHA", GIT_COMMIT)[:7],
        "build_timestamp": BUILD_TIMESTAMP,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "production_ready": True,
    }
