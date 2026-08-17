"""
Deterministic Rule Engine for Fast AI Moderation Pre-Processing.

Executes deterministic pattern matching, flood detection, repetition analysis,
and link safety checks with strict per-stream isolation and calibrated confidence.
"""

from collections import deque
import re
import time
from typing import Deque, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.moderation.models import (
    ActionSeverity,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
    ModerationSource,
    UserRole,
)
from app.services.youtube.models import ChatMessage

logger = get_logger("moderation.rules")

# Specifically suspicious URL patterns (Phishing TLDs, Telegram invite scams, IP loggers)
SUSPICIOUS_LINK_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:[a-zA-Z0-9-]+\.)+(?:xyz|top|tk|click|link|ru|pw|cc|monster|surf|rest|cam|work)/[^\s]*|"
    r"https?://(?:t\.me|telegram\.me)/\+[^\s]+|"
    r"https?://discord(?:\.gg|app\.com/invite)/[^\s]+|"
    r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^\s]*)",
    re.IGNORECASE,
)

# Known safe mainstream domains that must never be treated as malicious links
KNOWN_SAFE_DOMAINS_REGEX = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com|youtu\.be|google\.com|twitter\.com|x\.com|twitch\.tv|github\.com|wikipedia\.org)(?:/[^\s]*)?$",
    re.IGNORECASE,
)

SCAM_KEYWORDS_REGEX = re.compile(
    r"\b(crypto\s+giveaway|send\s+\d+(\.\d+)?\s*(btc|eth|sol)|claim\s+(free\s+)?(airdrop|nitro|crypto)|"
    r"whatsapp\s+me\s+at|dm\s+for\s+signals|guaranteed\s+profit\s+\d+%)\b",
    re.IGNORECASE,
)


class StreamRuleState:
    """Per-stream isolated state for flood tracking and message repetition."""

    def __init__(self):
        # author_id -> deque of timestamps
        self.user_message_timestamps: Dict[str, Deque[float]] = {}
        # author_id -> deque of (normalized_text, timestamp)
        self.user_message_history: Dict[str, Deque[Tuple[str, float]]] = {}

    def cleanup_old_data(self, now: float, cutoff_seconds: float = 60.0) -> None:
        """Purge tracking data older than cutoff."""
        for author_id in list(self.user_message_timestamps.keys()):
            q = self.user_message_timestamps[author_id]
            while q and now - q[0] > cutoff_seconds:
                q.popleft()
            if not q:
                del self.user_message_timestamps[author_id]

        for author_id in list(self.user_message_history.keys()):
            q = self.user_message_history[author_id]
            while q and now - q[0][1] > cutoff_seconds:
                q.popleft()
            if not q:
                del self.user_message_history[author_id]


class RuleEngine:
    """Deterministic Rule Engine partitioned by stream_id."""

    def __init__(self):
        self._stream_states: Dict[str, StreamRuleState] = {}

    def _get_stream_state(self, stream_id: str) -> StreamRuleState:
        if stream_id not in self._stream_states:
            self._stream_states[stream_id] = StreamRuleState()
        return self._stream_states[stream_id]

    def _normalize_text(self, text: str) -> str:
        """Normalize text for repetition comparison."""
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()

    def evaluate(self, msg: ChatMessage, role: UserRole = UserRole.USER) -> Optional[ModerationDecision]:
        """
        Evaluate chat message against fast deterministic rules.
        Returns ModerationDecision if a rule matches, otherwise None.
        """
        stream_id = msg.stream_id
        author_id = msg.author_id
        text = msg.message_text
        now = time.time()

        state = self._get_stream_state(stream_id)
        state.cleanup_old_data(now)

        # 1. Check Link Safety
        # Normal safe domains (e.g. youtube.com, google.com) are NOT malicious
        if SUSPICIOUS_LINK_REGEX.search(text):
            confidence = 0.95 if re.search(r"https?://\d{1,3}\.", text) else 0.92
            return ModerationDecision(
                message_id=msg.message_id,
                stream_id=stream_id,
                author_id=author_id,
                author_name=msg.author_name,
                user_role=role,
                category=ModerationCategory.MALICIOUS_LINK,
                confidence=confidence,
                severity=ActionSeverity.HIGH,
                reason="Detected suspicious or unverified external link pattern",
                recommended_action=ModerationAction.DELETE,
                source=ModerationSource.RULE_ENGINE,
            )

        # 2. Check Scam / Financial Fraud Keywords
        if SCAM_KEYWORDS_REGEX.search(text):
            return ModerationDecision(
                message_id=msg.message_id,
                stream_id=stream_id,
                author_id=author_id,
                author_name=msg.author_name,
                user_role=role,
                category=ModerationCategory.SCAM,
                confidence=0.92,
                severity=ActionSeverity.HIGH,
                reason="Detected cryptocurrency or financial fraud keywords",
                recommended_action=ModerationAction.DELETE,
                source=ModerationSource.RULE_ENGINE,
            )

        # 3. Check Message Flood (e.g. >= 5 messages within 4.0 seconds)
        if author_id not in state.user_message_timestamps:
            state.user_message_timestamps[author_id] = deque()
        timestamps = state.user_message_timestamps[author_id]
        timestamps.append(now)

        recent_in_window = [t for t in timestamps if now - t <= 4.0]
        if len(recent_in_window) >= 5:
            # Calibrated confidence: 5 msgs -> 0.90, 7+ msgs -> 0.98
            confidence = min(0.98, 0.90 + (len(recent_in_window) - 5) * 0.04)
            return ModerationDecision(
                message_id=msg.message_id,
                stream_id=stream_id,
                author_id=author_id,
                author_name=msg.author_name,
                user_role=role,
                category=ModerationCategory.FLOOD,
                confidence=confidence,
                severity=ActionSeverity.MEDIUM,
                reason=f"User sent {len(recent_in_window)} messages in 4.0 seconds",
                recommended_action=ModerationAction.SLOW_MODE,
                source=ModerationSource.RULE_ENGINE,
            )

        # 4. Check Repeated Message Spam
        normalized = self._normalize_text(text)
        if normalized and len(normalized) >= 4:
            if author_id not in state.user_message_history:
                state.user_message_history[author_id] = deque()
            history = state.user_message_history[author_id]
            history.append((normalized, now))

            # Check matching messages in last 30 seconds
            repeat_count = sum(1 for h_text, h_time in history if h_text == normalized and now - h_time <= 30.0)
            if repeat_count >= 3:
                # Calibrated confidence: 3 repeats -> 0.85, 4+ repeats -> 0.95
                confidence = 0.95 if repeat_count >= 4 else 0.85
                return ModerationDecision(
                    message_id=msg.message_id,
                    stream_id=stream_id,
                    author_id=author_id,
                    author_name=msg.author_name,
                    user_role=role,
                    category=ModerationCategory.REPEATED_MESSAGE,
                    confidence=confidence,
                    severity=ActionSeverity.LOW,
                    reason=f"User sent identical message {repeat_count} times in 30 seconds",
                    recommended_action=ModerationAction.DELETE,
                    source=ModerationSource.RULE_ENGINE,
                )

        # 5. Check Excessive Caps Spam (e.g., > 80% caps for text >= 15 chars)
        letters = [c for c in text if c.isalpha()]
        if len(letters) >= 15:
            upper_count = sum(1 for c in letters if c.isupper())
            ratio = upper_count / len(letters)
            if ratio >= 0.85:
                confidence = min(0.95, 0.80 + ratio * 0.15)
                return ModerationDecision(
                    message_id=msg.message_id,
                    stream_id=stream_id,
                    author_id=author_id,
                    author_name=msg.author_name,
                    user_role=role,
                    category=ModerationCategory.SPAM,
                    confidence=confidence,
                    severity=ActionSeverity.LOW,
                    reason="Excessive uppercase character spam (>= 85% caps)",
                    recommended_action=ModerationAction.WARN,
                    source=ModerationSource.RULE_ENGINE,
                )

        return None


# Global singleton instance of RuleEngine
rule_engine = RuleEngine()
