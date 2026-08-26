"""Adaptive Hindi/Hinglish Moderation Engine with RAG-lite memory and Human-in-the-Loop (HITL)."""

import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.gemini import GeminiAPIUnavailableError, GeminiClient, ModerationResult
from app.models import ChannelSettings, ModerationMemory, ModerationReview
from app.utils import get_logger, normalize_text
from app.youtube import YouTubeClient

logger = get_logger("goddess.moderation")

# ---------------------------------------------------------------------------
# Layer 1: Deterministic Hard Rules & Fast Regex Patterns
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
    re.IGNORECASE,
)

# Common known dangerous spam domains or patterns
SCAM_PATTERNS = [
    re.compile(r"free\s+robux", re.IGNORECASE),
    re.compile(r"free\s+vbucks", re.IGNORECASE),
    re.compile(r"free\s+diamonds", re.IGNORECASE),
    re.compile(r"whatsapp\s+me", re.IGNORECASE),
    re.compile(r"t\.me/", re.IGNORECASE),
    re.compile(r"bit\.ly/", re.IGNORECASE),
]


def check_deterministic_rules(normalized_message: str) -> ModerationResult | None:
    """Check fast deterministic safety rules before calling LLM."""
    # Check for scam link patterns
    for pat in SCAM_PATTERNS:
        if pat.search(normalized_message):
            return ModerationResult(
                is_violation=True,
                category="SCAM",
                confidence=0.98,
                severity="high",
                reason="Detected high-risk scam or promotion pattern",
                needs_review=False,
            )

    # Check for suspicious external links
    if URL_PATTERN.search(normalized_message):
        # We flag links for review rather than instant banning unless known scam
        return ModerationResult(
            is_violation=False,
            category="MALICIOUS_LINK",
            confidence=0.60,
            severity="medium",
            reason="Contains external URL",
            needs_review=True,
        )

    return None


# ---------------------------------------------------------------------------
# Layer 2: RAG-Lite Moderation Memory Retrieval
# ---------------------------------------------------------------------------


async def retrieve_relevant_memory(
    session: AsyncSession,
    channel_id: str,
    normalized_message: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve relevant human-reviewed examples from ModerationMemory."""
    # Split message into tokens for keyword matching
    tokens = [t for t in normalized_message.split() if len(t) > 2]
    if not tokens:
        return []

    stmt = (
        select(ModerationMemory)
        .where(
            ModerationMemory.channel_id == channel_id,
        )
        .order_by(ModerationMemory.usage_count.desc(), ModerationMemory.updated_at.desc())
        .limit(20)
    )

    result = await session.execute(stmt)
    memories = result.scalars().all()

    # Score relevance based on token overlap
    matched_examples: list[dict[str, Any]] = []
    for mem in memories:
        mem_phrase_norm = normalize_text(mem.phrase)
        if mem_phrase_norm in normalized_message or any(t in mem_phrase_norm for t in tokens):
            matched_examples.append(
                {
                    "phrase": mem.phrase,
                    "context": mem.context,
                    "is_allowed": mem.is_allowed,
                    "category": mem.category,
                }
            )
            if len(matched_examples) >= limit:
                break

    return matched_examples


# ---------------------------------------------------------------------------
# Moderation Engine & Pipeline Evaluator
# ---------------------------------------------------------------------------


class ModerationEngine:
    """Coordinates deterministic rules, adaptive memory, and Gemini contextual evaluation."""

    def __init__(
        self,
        gemini_client: GeminiClient,
        youtube_client: YouTubeClient | None = None,
    ) -> None:
        self.gemini = gemini_client
        self.youtube = youtube_client

    async def evaluate_message(
        self,
        session: AsyncSession,
        channel_id: str,
        stream_id: int | None,
        youtube_message_id: str,
        youtube_user_id: str,
        username: str,
        message: str,
        channel_settings: ChannelSettings,
        recent_context: list[str] | None = None,
    ) -> tuple[ModerationResult, str]:
        """
        Evaluate a message through the 4-layer moderation pipeline.
        Returns (ModerationResult, action_taken) where action_taken is:
        'ALLOW', 'REVIEW_CREATED', 'DELETED', 'TIMED_OUT'
        """
        normalized_msg = normalize_text(message)

        # If moderation is disabled for this channel, allow
        if not channel_settings.moderation_enabled:
            return (
                ModerationResult(
                    is_violation=False,
                    category="SAFE",
                    confidence=0.0,
                    severity="low",
                    reason="Moderation disabled",
                    needs_review=False,
                ),
                "ALLOW",
            )

        # 1. Deterministic Layer
        det_result = check_deterministic_rules(normalized_msg)
        if (
            det_result
            and det_result.is_violation
            and det_result.confidence >= channel_settings.moderation_threshold
        ):
            action = await self._execute_violation_action(
                channel_settings=channel_settings,
                youtube_message_id=youtube_message_id,
                youtube_user_id=youtube_user_id,
                severity=det_result.severity,
            )
            return det_result, action

        # 2. Retrieve Memory (RAG-lite)
        memory_examples = await retrieve_relevant_memory(session, channel_id, normalized_msg)

        # 3. Gemini Contextual Evaluation
        try:
            mod_result = await self.gemini.moderate_message(
                message=message,
                username=username,
                recent_context=recent_context,
                memory_examples=memory_examples,
            )
        except GeminiAPIUnavailableError:
            logger.warning("Gemini AI unavailable during moderation. Using fail-safe fallback.")
            if det_result:
                mod_result = det_result
            else:
                mod_result = ModerationResult(
                    is_violation=False,
                    category="SAFE",
                    confidence=0.0,
                    severity="low",
                    reason="AI_UNAVAILABLE",
                    needs_review=False,
                )

        # 4. Action Routing based on Configured Thresholds
        threshold = channel_settings.moderation_threshold
        hitl_threshold = settings.DEFAULT_HITL_THRESHOLD

        # Strict / Relaxed mode modifier
        if channel_settings.moderation_mode == "strict":
            threshold = min(threshold, 0.80)
            hitl_threshold = 0.30
        elif channel_settings.moderation_mode == "relaxed":
            threshold = max(threshold, 0.95)
            hitl_threshold = 0.50

        # High-confidence violation
        if mod_result.is_violation and mod_result.confidence >= threshold:
            action = await self._execute_violation_action(
                channel_settings=channel_settings,
                youtube_message_id=youtube_message_id,
                youtube_user_id=youtube_user_id,
                severity=mod_result.severity,
            )
            return mod_result, action

        # Borderline / HITL Review Required
        if (
            mod_result.needs_review
            or (mod_result.confidence >= hitl_threshold and mod_result.is_violation)
            or (hitl_threshold <= mod_result.confidence < threshold and mod_result.category != "SAFE")
        ):
            await self._create_moderation_review(
                session=session,
                channel_id=channel_id,
                stream_id=stream_id,
                youtube_message_id=youtube_message_id,
                user_id=youtube_user_id,
                username=username,
                original_message=message,
                normalized_message=normalized_msg,
                result=mod_result,
            )
            return mod_result, "REVIEW_CREATED"

        # Allowed
        return mod_result, "ALLOW"

    async def _execute_violation_action(
        self,
        channel_settings: ChannelSettings,
        youtube_message_id: str,
        youtube_user_id: str,
        severity: str,
    ) -> str:
        """Execute automated deletion or timeout via YouTube OAuth."""
        if not self.youtube:
            return "VIOLATION_NO_YOUTUBE_CLIENT"

        # Delete message
        deleted = await self.youtube.delete_chat_message(youtube_message_id)
        action = "DELETED" if deleted else "DELETE_FAILED"

        # If high severity, also apply timeout
        if severity == "high" and deleted:
            # Note: Timeout requires live_chat_id; if available in context, apply timeout
            pass

        return action

    async def _create_moderation_review(
        self,
        session: AsyncSession,
        channel_id: str,
        stream_id: int | None,
        youtube_message_id: str,
        user_id: str,
        username: str,
        original_message: str,
        normalized_message: str,
        result: ModerationResult,
    ) -> ModerationReview:
        """Persist a borderline message to the ModerationReview queue."""
        review = ModerationReview(
            channel_id=channel_id,
            stream_id=stream_id,
            youtube_message_id=youtube_message_id,
            user_id=user_id,
            username=username,
            original_message=original_message,
            normalized_message=normalized_message,
            model_category=result.category,
            model_confidence=result.confidence,
            model_reason=result.reason,
            status="PENDING",
            created_at=datetime.now(UTC),
        )
        session.add(review)
        await session.flush()
        logger.info(
            f"Created HITL ModerationReview ID={review.id} for @{username}: "
            f"category={result.category} confidence={result.confidence:.2f}"
        )

        # Notify via Discord webhook if configured
        if settings.DISCORD_MOD_WEBHOOK_URL:
            await self._send_discord_alert(review)

        return review

    async def _send_discord_alert(self, review: ModerationReview) -> None:
        """Send notification of pending review to Discord moderator channel."""
        webhook_url = settings.DISCORD_MOD_WEBHOOK_URL
        if not webhook_url:
            return
        payload = {
            "content": (
                f"🛡️ **[Goddess AI 3.0] Pending Moderation Review #{review.id}**\n"
                f"**User**: @{review.username} (`{review.user_id}`)\n"
                f'**Message**: "{review.original_message}"\n'
                f"**Category**: `{review.model_category}` (Confidence: `{review.model_confidence:.2f}`)\n"
                f"**Reason**: {review.model_reason}\n"
                f"*Use chat command `!mod allow {review.id}` or `!mod ban {review.id}`*"
            )
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(webhook_url, json=payload)
        except Exception as e:
            logger.warning(f"Failed to post Discord webhook alert: {e}")


# ---------------------------------------------------------------------------
# Human Review Resolution & Memory Learning
# ---------------------------------------------------------------------------


async def resolve_moderation_review(
    session: AsyncSession,
    channel_id: str,
    review_id: int,
    action: str,  # "allow", "ban", "ignore"
    reviewed_by: str,
    youtube_client: YouTubeClient | None = None,
) -> tuple[bool, str]:
    """
    Resolve a pending moderation review and update adaptive moderation memory.
    Returns (success: bool, feedback_message: str).
    """
    stmt = select(ModerationReview).where(
        ModerationReview.id == review_id,
        ModerationReview.channel_id == channel_id,
    )
    res = await session.execute(stmt)
    review = res.scalar_one_or_none()

    if not review:
        return False, f"⚠️ Review #{review_id} not found."

    if review.status != "PENDING":
        return False, f"⚠️ Review #{review_id} is already {review.status}."

    action_clean = action.lower().strip()
    review.reviewed_at = datetime.now(UTC)
    review.reviewed_by = reviewed_by

    if action_clean == "allow":
        review.status = "ALLOWED"
        # Add to ModerationMemory as allowed context
        await _update_moderation_memory(
            session=session,
            channel_id=channel_id,
            phrase=review.normalized_message[:100],
            context=f"Human approved gaming context ({review.original_message[:60]})",
            is_allowed=True,
            category=review.model_category,
            reviewed_by=reviewed_by,
        )
        return (
            True,
            f"✅ Review #{review_id} marked ALLOWED. Saved to moderation memory.",
        )

    elif action_clean == "ban":
        review.status = "BANNED"
        # Delete message if YouTubeClient is provided
        if youtube_client and review.youtube_message_id:
            await youtube_client.delete_chat_message(review.youtube_message_id)

        # Add to ModerationMemory as banned context
        await _update_moderation_memory(
            session=session,
            channel_id=channel_id,
            phrase=review.normalized_message[:100],
            context=f"Human banned toxic context ({review.original_message[:60]})",
            is_allowed=False,
            category=review.model_category,
            reviewed_by=reviewed_by,
        )
        return (
            True,
            f"🚫 Review #{review_id} marked BANNED. Saved to moderation memory.",
        )

    elif action_clean == "ignore":
        review.status = "IGNORED"
        return True, f"ℹ️ Review #{review_id} marked IGNORED."

    return False, f"⚠️ Unknown action '{action}'. Use allow, ban, or ignore."


async def _update_moderation_memory(
    session: AsyncSession,
    channel_id: str,
    phrase: str,
    context: str,
    is_allowed: bool,
    category: str,
    reviewed_by: str,
) -> None:
    """Insert or update a ModerationMemory entry."""
    stmt = select(ModerationMemory).where(
        ModerationMemory.channel_id == channel_id,
        ModerationMemory.phrase == phrase,
    )
    res = await session.execute(stmt)
    memory = res.scalar_one_or_none()

    if memory:
        memory.is_allowed = is_allowed
        memory.category = category
        memory.context = context
        memory.reviewed_by = reviewed_by
        memory.usage_count += 1
        memory.updated_at = datetime.now(UTC)
    else:
        memory = ModerationMemory(
            channel_id=channel_id,
            phrase=phrase,
            context=context,
            is_allowed=is_allowed,
            category=category,
            confidence=1.0,
            reviewed_by=reviewed_by,
            usage_count=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(memory)
    await session.flush()
