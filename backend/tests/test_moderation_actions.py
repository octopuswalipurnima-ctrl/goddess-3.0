"""
Tests for YouTubeModerationExecutor and Idempotency Protection.
"""

import pytest
from app.services.moderation.actions import YouTubeModerationExecutor
from app.services.moderation.exceptions import DuplicateActionError
from app.services.moderation.models import (
    ActionStatus,
    ModerationAction,
    ModerationCategory,
    ModerationDecision,
)


@pytest.mark.asyncio
async def test_action_executor_successful_execution():
    """Verify execution of approved moderation action."""
    executor = YouTubeModerationExecutor()
    dec = ModerationDecision(
        message_id="msg_exec_1",
        stream_id="stream_1",
        author_id="u1",
        author_name="User1",
        category=ModerationCategory.SPAM,
        recommended_action=ModerationAction.DELETE,
    )

    status = await executor.execute(dec, ModerationAction.DELETE)
    assert status == ActionStatus.EXECUTED


@pytest.mark.asyncio
async def test_action_executor_idempotency_duplicate_protection():
    """Verify that re-executing the same action on the same message raises DuplicateActionError."""
    executor = YouTubeModerationExecutor()
    dec = ModerationDecision(
        message_id="msg_dup_1",
        stream_id="stream_1",
        author_id="u2",
        author_name="User2",
        category=ModerationCategory.MALICIOUS_LINK,
        recommended_action=ModerationAction.DELETE,
    )

    # First execution succeeds
    await executor.execute(dec, ModerationAction.DELETE)

    # Second execution MUST raise DuplicateActionError
    with pytest.raises(DuplicateActionError):
        await executor.execute(dec, ModerationAction.DELETE)
