"""
Structured Logging Configuration for GODDESS AI 2.0.

Provides standard formatting with service, stream context, and automatic secret redaction.
"""

import logging
import re
import sys
from typing import Optional


# Regular expressions for identifying common API key patterns to redact
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google/YouTube/Gemini API keys
    re.compile(r"(api[-_]?key[\"'\s:=]+)([\"']?[a-zA-Z0-9_\-]{8,}[\"']?)", re.IGNORECASE),
    re.compile(r"(password[\"'\s:=]+)([\"']?[^\s\"',]{4,}[\"']?)", re.IGNORECASE),
    re.compile(r"(secret[\"'\s:=]+)([\"']?[^\s\"',]{8,}[\"']?)", re.IGNORECASE),
]


class SecretRedactingFormatter(logging.Formatter):
    """Log formatter that automatically masks API keys and secrets."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        return redacted


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
