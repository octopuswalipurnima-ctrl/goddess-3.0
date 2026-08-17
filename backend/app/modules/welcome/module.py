"""
Welcome Module for GODDESS AI 2.0.

Detects new and returning chat participants and delivers configurable welcome greetings
with cooldown protection and default disabled state.
"""

from collections import OrderedDict
import time
from typing import Any, Dict, Optional

from app.core.events import event_bus
from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.models import ModuleCapability, ModuleMetadata
from app.services.youtube.models import ChatMessage
from app.services.youtube.stream_manager import stream_manager

logger = get_logger("modules.welcome")


class WelcomeModule(BaseModule):
    """Greets new viewers in live chat with cooldown and anti-spam constraints."""

    def __init__(self):
        metadata = ModuleMetadata(
            id="welcome",
            name="Viewer Welcome",
            version="1.0.0",
            description="Greets first-time and returning viewers in live chat.",
            category="interaction",
            capabilities=[ModuleCapability.CHAT_READ, ModuleCapability.CHAT_WRITE],
            supported_events=["CHAT_MESSAGE"],
        )
        super().__init__(metadata)

        # stream_id -> OrderedDict of (author_id -> last_welcomed_timestamp)
        self._welcomed_users: Dict[str, OrderedDict[str, float]] = {}
        self.metrics = {"welcomes_sent": 0}

    async def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Handle incoming CHAT_MESSAGE events."""
        if event_name != "CHAT_MESSAGE":
            return

        try:
            msg = ChatMessage(**event_data)
        except Exception:
            return

        stream_id = msg.stream_id
        config = self.get_stream_config(stream_id)
        if not config.enabled:
            return  # Default is disabled

        author_id = msg.author_id
        if stream_id not in self._welcomed_users:
            self._welcomed_users[stream_id] = OrderedDict()

        seen_dict = self._welcomed_users[stream_id]
        now = time.time()
        cooldown_sec = config.settings.get("welcome_cooldown_sec", 300.0)

        # Check if user has already been welcomed recently
        if author_id in seen_dict and now - seen_dict[author_id] < cooldown_sec:
            return

        # Record welcome timestamp and enforce memory bound (max 1000 users)
        seen_dict[author_id] = now
        if len(seen_dict) > 1000:
            seen_dict.popitem(last=False)

        greeting_template = config.settings.get(
            "greeting_template", "Welcome to the stream, {username}! Glad to have you here!"
        )
        greeting = greeting_template.format(username=msg.author_name)

        try:
            session = stream_manager.get_session(stream_id)
            if session and session.is_active:
                await session.send_chat_message(greeting)
            self.metrics["welcomes_sent"] += 1
            await event_bus.publish(
                "VIEWER_WELCOMED",
                {
                    "stream_id": stream_id,
                    "author_id": author_id,
                    "author_name": msg.author_name,
                    "greeting": greeting,
                },
            )
        except Exception as exc:
            logger.debug(f"Failed to post welcome message to YouTube: {exc}")
