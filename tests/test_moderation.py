"""Tests for Hindi/Hinglish normalization, moderation engine, HITL reviews, and memory."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini import ModerationResult
from app.models import (
    Channel,
    ChannelSettings,
    ModerationMemory,
    ModerationReview,
    Stream,
)
from app.moderation import (
    ModerationEngine,
    check_deterministic_rules,
    resolve_moderation_review,
    retrieve_relevant_memory,
)
from app.utils import normalize_text


def test_text_normalization():
    """Test conservative text normalization for Hinglish and repeated characters."""
    assert normalize_text("bhaiiiii") == "bhaii"
    assert normalize_text("NOOOOOB") == "noob"
    assert normalize_text("  kya   scene  hai  brooo  ") == "kya scene hai broo"
    assert normalize_text("HELLOOO WORLD!!!") == "helloo world!!"


def test_deterministic_rules_scam():
    """Test deterministic rule detection on obvious scam spam."""
    res = check_deterministic_rules("get free robux at http://free-robux.xyz")
    assert res is not None
    assert res.is_violation is True
    assert res.category == "SCAM"
    assert res.confidence >= 0.90


@pytest.mark.asyncio
async def test_moderation_hitl_review_creation(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that borderline messages generate a ModerationReview."""
    channel, channel_settings, stream = setup_channel_and_stream

    # Mock GeminiClient that returns a borderline result
    class MockBorderlineGemini:
        async def moderate_message(self, *args, **kwargs) -> ModerationResult:
            return ModerationResult(
                is_violation=False,
                category="TOXICITY",
                confidence=0.65,
                severity="medium",
                reason="Contextually ambiguous banter",
                needs_review=True,
            )

    engine = ModerationEngine(gemini_client=MockBorderlineGemini())  # type: ignore

    res, action = await engine.evaluate_message(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        youtube_message_id="msg_test_123",
        youtube_user_id="yt_user_1",
        username="GamerBoy",
        message="pagal hai kya tu",
        channel_settings=channel_settings,
    )

    assert action == "REVIEW_CREATED"
    assert res.confidence == 0.65

    # Verify review in DB
    stmt = select(ModerationReview).where(ModerationReview.youtube_message_id == "msg_test_123")
    db_res = await db_session.execute(stmt)
    review = db_res.scalar_one_or_none()

    assert review is not None
    assert review.status == "PENDING"
    assert review.username == "GamerBoy"


@pytest.mark.asyncio
async def test_moderation_review_resolution_and_memory(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test resolving a review with allow and verifying learning memory."""
    channel, channel_settings, stream = setup_channel_and_stream

    # Create a pending review
    review = ModerationReview(
        channel_id=channel.channel_id,
        stream_id=stream.id,
        youtube_message_id="msg_test_456",
        user_id="yt_user_2",
        username="FriendlyGuy",
        original_message="chal nikal bhai",
        normalized_message="chal nikal bhai",
        model_category="TOXICITY",
        model_confidence=0.60,
        model_reason="Possible insult",
        status="PENDING",
    )
    db_session.add(review)
    await db_session.commit()

    # Resolve with allow
    success, msg = await resolve_moderation_review(
        session=db_session,
        channel_id=channel.channel_id,
        review_id=review.id,
        action="allow",
        reviewed_by="StreamerMod",
    )
    assert success is True
    assert "ALLOWED" in msg

    # Check ModerationMemory
    stmt = select(ModerationMemory).where(
        ModerationMemory.channel_id == channel.channel_id,
    )
    mem_res = await db_session.execute(stmt)
    memories = mem_res.scalars().all()

    assert len(memories) >= 1
    assert memories[0].is_allowed is True
    assert "chal nikal bhai" in memories[0].phrase

    # Test retrieval of this memory
    retrieved = await retrieve_relevant_memory(db_session, channel.channel_id, "chal nikal bhai")
    assert len(retrieved) >= 1
    assert retrieved[0]["is_allowed"] is True
