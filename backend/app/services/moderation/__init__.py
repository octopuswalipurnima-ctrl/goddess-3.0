"""
AI Moderation Service Package for GODDESS AI 2.0.

Exports rule engine, Gemini classifier, action policy, moderation executor,
audit logger, and centralized moderation manager.
"""

from app.services.moderation.actions import (
    YouTubeModerationExecutor,
    moderation_executor,
)
from app.services.moderation.audit import (
    ModerationAuditLogger,
    moderation_audit_logger,
)
from app.services.moderation.classifier import (
    GeminiModerationClassifier,
    gemini_moderation_classifier,
)
from app.services.moderation.exceptions import (
    ActionBlockedError,
    ActionExecutionError,
    DuplicateActionError,
    InvalidModerationConfigError,
    ModerationError,
)
from app.services.moderation.manager import (
    ModerationManager,
    moderation_manager,
)
from app.services.moderation.models import (
    ActionSeverity,
    ActionStatus,
    ModerationAction,
    ModerationAuditRecord,
    ModerationCategory,
    ModerationDecision,
    ModerationMetrics,
    ModerationSource,
    StreamModerationConfig,
    UserRole,
)
from app.services.moderation.policy import (
    ActionPolicy,
    action_policy,
)
from app.services.moderation.rules import (
    RuleEngine,
    rule_engine,
)

__all__ = [
    "RuleEngine",
    "rule_engine",
    "GeminiModerationClassifier",
    "gemini_moderation_classifier",
    "ActionPolicy",
    "action_policy",
    "YouTubeModerationExecutor",
    "moderation_executor",
    "ModerationAuditLogger",
    "moderation_audit_logger",
    "ModerationManager",
    "moderation_manager",
    "ModerationCategory",
    "ModerationAction",
    "ActionSeverity",
    "UserRole",
    "ModerationSource",
    "ActionStatus",
    "ModerationDecision",
    "ModerationAuditRecord",
    "StreamModerationConfig",
    "ModerationMetrics",
    "ModerationError",
    "ActionBlockedError",
    "ActionExecutionError",
    "DuplicateActionError",
    "InvalidModerationConfigError",
]
