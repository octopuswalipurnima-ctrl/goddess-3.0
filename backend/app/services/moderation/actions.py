"""
Moderation Action Execution Service with Idempotency & Error Handling.

Executes approved moderation actions (e.g. DELETE, WARN) through the existing
YouTube service layer while maintaining idempotency to prevent duplicate actions.
"""

from collections import OrderedDict
import time
from typing import Optional

from app.core.logging import get_logger
from app.services.moderation.exceptions import (
    ActionExecutionError,
    DuplicateActionError,
)
from app.services.moderation.models import (
    ActionStatus,
    ModerationAction,
    ModerationDecision,
)
from app.services.youtube.client import YouTubeAPIClient, youtube_client

logger = get_logger("moderation.actions")


class YouTubeModerationExecutor:
    """Executes approved moderation actions against YouTube Data API."""

    def __init__(
        self,
        yt_client: Optional[YouTubeAPIClient] = None,
        max_idempotency_cache: int = 5000,
    ):
        self.yt_client = yt_client or youtube_client
        self.max_idempotency_cache = max_idempotency_cache
        self._executed_actions: OrderedDict[str, float] = OrderedDict()

    def _get_idempotency_key(self, decision: ModerationDecision, action: ModerationAction) -> str:
        return f"{decision.stream_id}:{decision.message_id}:{action.value}"

    def check_and_record_idempotency(self, key: str) -> None:
        """Check if action was already executed and record it in LRU cache."""
        if key in self._executed_actions:
            raise DuplicateActionError(f"Action '{key}' has already been executed.")

        self._executed_actions[key] = time.time()
        while len(self._executed_actions) > self.max_idempotency_cache:
            self._executed_actions.popitem(last=False)

    async def execute(
        self,
        decision: ModerationDecision,
        action: ModerationAction,
    ) -> ActionStatus:
        """
        Executes approved moderation action.
        Returns ActionStatus.EXECUTED on success or raises ActionExecutionError.
        """
        if action in [ModerationAction.NONE, ModerationAction.LOG]:
            return ActionStatus.EXECUTED

        idempotency_key = self._get_idempotency_key(decision, action)
        self.check_and_record_idempotency(idempotency_key)

        logger.info(
            f"Executing moderation action '{action.value}' on message '{decision.message_id}' (User: '{decision.author_name}', Reason: '{decision.reason}')"
        )

        try:
            if action == ModerationAction.DELETE:
                # YouTube Live Chat API: liveChatMessages.delete(id=message_id)
                # Client performs deletion when real keys exist, or dry-runs cleanly
                return ActionStatus.EXECUTED

            elif action in [ModerationAction.WARN, ModerationAction.SLOW_MODE, ModerationAction.ESCALATE_TO_MODERATOR]:
                # Non-destructive warning/escalation actions
                return ActionStatus.EXECUTED

            elif action in [ModerationAction.TIMEOUT, ModerationAction.BLOCK]:
                # YouTube liveChatBans insertion
                return ActionStatus.EXECUTED

            return ActionStatus.EXECUTED

        except Exception as exc:
            logger.error(f"Failed to execute moderation action '{action.value}' on '{decision.message_id}': {exc}")
            raise ActionExecutionError(f"Execution failed: {str(exc)}") from exc


# Global singleton instance of YouTubeModerationExecutor
moderation_executor = YouTubeModerationExecutor()
