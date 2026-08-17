"""
Custom Exception Hierarchy for AI Moderation Engine in GODDESS AI 2.0.
"""


class ModerationError(Exception):
    """Base exception for moderation engine operations."""
    pass


class ActionBlockedError(ModerationError):
    """Raised when an action is rejected by the ActionPolicy gate."""
    pass


class ActionExecutionError(ModerationError):
    """Raised when execution of a moderation action fails on provider API."""
    pass


class DuplicateActionError(ModerationError):
    """Raised when an action is dropped because it has already been executed (idempotency)."""
    pass


class InvalidModerationConfigError(ModerationError):
    """Raised when stream moderation configuration is invalid."""
    pass
