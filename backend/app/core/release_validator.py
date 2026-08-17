"""
Production Release Gate and Readiness Validator for GODDESS AI 2.0.

Provides deep comprehensive pre-flight verification of configuration, secrets,
database migrations, Redis coordination, provider credentials, and safety controllers
before permitting uninhibited live production operation.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.core.validator import validate_production_configuration
from app.core.version import APP_VERSION

logger = get_logger("core.release_validator")


class ReleaseValidationResult(BaseModel):
    """Immutable audit report from production release gate."""
    passed: bool
    production_ready: bool
    version: str = APP_VERSION
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class ProductionReleaseValidator:
    """Pre-flight and live release gate validator."""

    def __init__(self, cfg: Optional[Settings] = None):
        self.settings = cfg or settings

    async def validate_release(self) -> ReleaseValidationResult:
        """
        Execute exhaustive checks across all subsystem gates.
        Guarantees zero raw secrets in return payload.
        """
        checks: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []
        blockers: List[str] = []

        is_production = self.settings.environment.lower() == "production"

        # 1. Environment & Mode Check
        checks["environment"] = {
            "status": "PASS" if (not is_production or not self.settings.debug) else "FAIL",
            "environment": self.settings.environment,
            "debug": self.settings.debug,
        }
        if is_production and self.settings.debug:
            blockers.append("DEBUG mode must be disabled (False) in production.")

        # 2. Base Configuration & Secrets
        try:
            is_valid, cfg_issues, diag = validate_production_configuration(self.settings)
            checks["configuration"] = {
                "status": "PASS" if is_valid else ("FAIL" if is_production else "WARN"),
                "issues": cfg_issues,
                "summary": diag.get("safe_summary", {}),
            }
            if not is_valid:
                if is_production:
                    blockers.extend(cfg_issues)
                else:
                    warnings.extend(cfg_issues)
        except Exception as exc:
            checks["configuration"] = {"status": "FAIL", "error": str(exc)}
            blockers.append(f"Configuration validation exception: {exc}")

        # 3. Database Connectivity
        from app.db.session import ping_database
        try:
            db_res = await ping_database()
            checks["database"] = {
                "status": "PASS" if db_res["status"] in ["HEALTHY", "NOT_CONFIGURED"] else "FAIL",
                "details": db_res["details"],
            }
            if is_production and not self.settings.is_database_configured:
                blockers.append("PostgreSQL DATABASE_URL is mandatory in production.")
            elif db_res["status"] == "UNAVAILABLE":
                blockers.append("PostgreSQL database is unreachable.")
        except Exception as exc:
            checks["database"] = {"status": "FAIL", "error": str(exc)}
            if is_production:
                blockers.append(f"Database error: {exc}")

        # 4. Redis Coordination
        from app.core.redis import redis_state
        try:
            r_res = await redis_state.ping()
            checks["redis"] = {
                "status": "PASS" if r_res["status"] in ["HEALTHY", "DEGRADED", "NOT_CONFIGURED"] else "WARN",
                "mode": r_res.get("mode", "in-memory-fallback"),
            }
        except Exception as exc:
            checks["redis"] = {"status": "WARN", "error": str(exc)}
            warnings.append(f"Redis notice: {exc}")

        # 5. YouTube Provider
        from app.services.youtube.credentials import youtube_credentials
        yt_summary = youtube_credentials.get_health_summary()
        yt_avail = sum(1 for c in yt_summary if c.state.value == "AVAILABLE")
        checks["youtube"] = {
            "status": "PASS" if (yt_avail > 0 or not is_production) else "FAIL",
            "available_slots": yt_avail,
            "total_slots": len(yt_summary),
        }
        if is_production and yt_avail == 0:
            blockers.append("No active YouTube credentials available in production.")

        # 6. Gemini Provider
        from app.services.gemini.credentials import gemini_credentials
        g_summary = gemini_credentials.get_health_summary()
        g_avail = sum(1 for c in g_summary if c.state.value == "AVAILABLE")
        checks["gemini"] = {
            "status": "PASS" if (g_avail > 0 or not is_production) else "FAIL",
            "available_slots": g_avail,
            "total_slots": len(g_summary),
        }
        if is_production and g_avail == 0:
            blockers.append("No active Gemini credentials available in production.")

        # 7. ProductionSafetyController Availability
        from app.core.safety_controller import safety_controller
        checks["safety_controller"] = {
            "status": "PASS" if safety_controller else "FAIL",
            "global_state": safety_controller.global_state.value,
        }
        if not safety_controller:
            blockers.append("ProductionSafetyController is unavailable.")

        # 8. StreamSupervisor Availability
        from app.services.youtube.stream_supervisor import stream_supervisor
        checks["stream_supervisor"] = {
            "status": "PASS" if stream_supervisor else "FAIL",
            "active_streams": stream_supervisor.active_stream_count,
        }

        # 9. RBAC & Security
        checks["rbac"] = {
            "status": "PASS" if self.settings.auth_enabled else ("FAIL" if is_production else "WARN"),
            "auth_enabled": self.settings.auth_enabled,
            "dev_bypass": self.settings.auth_dev_bypass,
        }

        passed = len(blockers) == 0
        production_ready = passed and len(warnings) == 0

        return ReleaseValidationResult(
            passed=passed,
            production_ready=production_ready,
            checks=checks,
            warnings=warnings,
            blockers=blockers,
        )


# Global singleton
release_validator = ProductionReleaseValidator()
