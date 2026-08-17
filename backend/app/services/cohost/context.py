"""
Short-Term Conversational Context Manager for AI Co-Host in GODDESS AI 2.0.

Maintains bounded rolling conversational memory per stream (max 20 messages)
and limited short-term history per user (max 5 interactions) with strict stream isolation.
"""

from collections import deque
import time
from typing import Deque, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.cohost.models import CoHostMessage

logger = get_logger("cohost.context")


class StreamContext:
    """Bounded, isolated conversational memory for a single stream session."""

    def __init__(
        self,
        stream_id: str,
        max_stream_messages: int = 20,
        max_user_messages: int = 5,
    ):
        self.stream_id = stream_id
        self.max_stream_messages = max_stream_messages
        self.max_user_messages = max_user_messages

        # deque of (role, author_name, message_text, timestamp)
        self.stream_history: Deque[Tuple[str, str, str, float]] = deque(maxlen=max_stream_messages)
        # author_id -> deque of (message_text, timestamp)
        self.user_history: Dict[str, Deque[Tuple[str, float]]] = {}

    def add_viewer_message(self, msg: CoHostMessage) -> None:
        """Record an incoming viewer message in stream and user sliding buffers."""
        now = time.time()
        self.stream_history.append(("viewer", msg.author_name, msg.message_text, now))

        if msg.author_id not in self.user_history:
            self.user_history[msg.author_id] = deque(maxlen=self.max_user_messages)
        self.user_history[msg.author_id].append((msg.message_text, now))

    def add_cohost_response(self, response_text: str, persona_name: str = "Goddess") -> None:
        """Record an approved co-host response in the stream conversation history."""
        self.stream_history.append(("cohost", persona_name, response_text, time.time()))

    def get_formatted_context(self, current_author_id: Optional[str] = None) -> str:
        """
        Formats recent relevant conversation history into a concise context block for Gemini.
        """
        lines: List[str] = []

        # 1. Recent stream chat history
        if self.stream_history:
            lines.append("Recent Stream Chat:")
            for role, name, text, _ in list(self.stream_history)[-8:]:
                prefix = "Co-Host" if role == "cohost" else f"Viewer ({name})"
                lines.append(f"- {prefix}: {text}")

        # 2. Prior interaction history for this specific user
        if current_author_id and current_author_id in self.user_history:
            u_msgs = list(self.user_history[current_author_id])
            if len(u_msgs) > 1:  # Only if they have previous messages before the current one
                lines.append("This viewer's recent messages:")
                for text, _ in u_msgs[-3:]:
                    lines.append(f"  * {text}")

        return "\n".join(lines)


class CoHostContextManager:
    """Manages short-term conversation contexts strictly partitioned by stream_id."""

    def __init__(self):
        self._contexts: Dict[str, StreamContext] = {}

    def get_context(
        self,
        stream_id: str,
        max_stream_messages: int = 20,
        max_user_messages: int = 5,
    ) -> StreamContext:
        """Retrieve or initialize stream context."""
        if stream_id not in self._contexts:
            self._contexts[stream_id] = StreamContext(
                stream_id=stream_id,
                max_stream_messages=max_stream_messages,
                max_user_messages=max_user_messages,
            )
        return self._contexts[stream_id]

    def clear_context(self, stream_id: str) -> None:
        """Clean up memory when a stream ends."""
        if stream_id in self._contexts:
            del self._contexts[stream_id]
            logger.info(f"Cleared CoHostContext for stream '{stream_id}'.")


# Global singleton context manager
cohost_context_manager = CoHostContextManager()
