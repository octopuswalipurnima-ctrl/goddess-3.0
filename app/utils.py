"""Utility functions: structured logging, secret masking, text normalization, and cooldowns."""

import json
import logging
import re
import sys
import unicodedata
from datetime import UTC, datetime
from typing import Any


def mask_secret(secret: str | None, visible_chars: int = 4) -> str:
    """Mask a secret string for safe logging."""
    if not secret:
        return "[NOT_SET]"
    if len(secret) <= visible_chars * 2:
        return "***"
    return f"{secret[:visible_chars]}...{secret[-visible_chars:]}"


class StructuredFormatter(logging.Formatter):
    """Formats logs in a clean, consistent key-value format suitable for Railway."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(5)
        name = record.name
        message = record.getMessage()

        # Extract extra structured fields if present
        extra_fields = []
        for key, val in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            ):
                # Ensure no secrets in extra fields
                val_str = str(val)
                extra_fields.append(f"{key}={val_str}")

        extras = " ".join(extra_fields)
        if extras:
            return f"[{timestamp}] [{level}] [{name}] {message} | {extras}"
        return f"[{timestamp}] [{level}] [{name}] {message}"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with structured formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    # Suppress excessive logging from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


logger = get_logger("goddess.utils")

# ---------------------------------------------------------------------------
# Text Normalization
# ---------------------------------------------------------------------------

# Repeated characters pattern (3 or more identical characters -> 1 or 2)
REPEATED_CHARS_RE = re.compile(r"(.)\1{2,}", re.IGNORECASE)

# Multiple spaces and control characters
WHITESPACE_RE = re.compile(r"\s+")

# Common Hinglish leetspeak / phonetic substitutions for comparison
LEETSPEAK_MAP = {
    "@": "a",
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "$": "s",
    "!": "i",
}

# Common Hinglish phonetic variants normalization dictionary
HINGLISH_VARIANTS = {
    "bhaai": "bhai",
    "bhaaii": "bhai",
    "bhaiya": "bhai",
    "brooo": "bro",
    "plzzz": "please",
    "plzz": "please",
    "pls": "please",
    "ty": "thank you",
    "thx": "thanks",
    "kya": "kya",
    "kyu": "kyun",
    "kyuu": "kyun",
    "kaise": "kaise",
    "kese": "kaise",
    "haan": "haan",
    "haa": "haan",
    "hnn": "haan",
    "hn": "haan",
    "yrr": "yaar",
    "yr": "yaar",
    "noobda": "noob",
    "noobie": "noob",
    "bottt": "bot",
    "prooo": "pro",
}


def normalize_text(text: str) -> str:
    """
    Perform conservative, context-preserving normalization:
    1. Unicode NFKC normalization
    2. Lowercase
    3. Collapse repeated characters (e.g., 'nooooob' -> 'noob')
    4. Collapse excessive whitespace
    5. Clean leading/trailing punctuation
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Lowercase
    normalized = normalized.lower().strip()

    # 3. Collapse repeated characters (3+ occurrences down to 2)
    normalized = REPEATED_CHARS_RE.sub(r"\1\1", normalized)

    # 4. Collapse whitespace
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()

    return normalized


def extract_json_from_llm_response(raw_text: str) -> dict[str, Any] | None:
    """Extract and parse a JSON object from raw LLM output, handling markdown fences."""
    if not raw_text:
        return None

    cleaned = raw_text.strip()

    # Remove markdown code block if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Try direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Try finding first { and matching }
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"Failed to parse JSON substring: {e}")

    return None
