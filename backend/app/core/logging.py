"""
Structured Logging Configuration for GODDESS AI 2.0.

Provides standard formatting with service, stream context, and automatic secret redaction.
"""

import logging
import re
import sys
from typing import Optional


# Regular expressions and replacement patterns for identifying API keys to redact
SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z\-_]{33,37}"), "[REDACTED_API_KEY]"),
    (re.compile(r"(api[-_]?key[\"'\s:=]+)([\"']?[a-zA-Z0-9_\-]{8,}[\"']?)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(password[\"'\s:=]+)([\"']?[^\s\"',]{4,}[\"']?)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(secret[\"'\s:=]+)([\"']?[^\s\"',]{8,}[\"']?)", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-\._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED]"),
]


class SecretRedactingFormatter(logging.Formatter):
    """Log formatter that automatically masks API keys and secrets safely."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            original = super().format(record)
            redacted = original
            for pattern, repl in SECRET_PATTERNS:
                redacted = pattern.sub(repl, redacted)
            return redacted
        except Exception:
            return super().format(record)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Initialize root logger with formatted console handler and secret protection."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger("goddess")
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)

        formatter = SecretRedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a child logger with consistent prefix."""
    if name:
        return logging.getLogger(f"goddess.{name}")
    return logging.getLogger("goddess")
