"""
Commands Module for GODDESS AI 2.0.

Provides safe, prefix-based chat commands (!help, !discord, !socials, !rules)
with per-command and per-user cooldowns, stream isolation, and zero arbitrary code execution.
"""

import re
import time
from typing import Any, Dict, Optional, Tuple

from app.core.events import event_bus
from app.core.logging import get_logger
from app.modules.base import BaseModule
from app.modules.models import ModuleCapability, ModuleMetadata
from app.services.youtube.models import ChatMessage
from app.services.youtube.stream_manager import stream_manager

logger = get_logger("modules.commands")

DEFAULT_COMMANDS = {
    "help": "Available commands: !help, !discord, !socials, !rules",
    "discord": "Join our official community Discord: https://discord.gg/example",
    "socials": "Follow our socials: Twitter @GoddessLive | YouTube @GoddessAI",
    "rules": "Stream Rules: Be respectful, no spamming, no hate speech, enjoy the stream!",
}


class CommandsModule(BaseModule):
    """Handles prefix chat commands safely with cooldowns and stream isolation."""

    def __init__(self):
        metadata = ModuleMetadata(
            id="commands",
            name="Chat Commands",
            version="1.0.0",
            description="Executes safe static chat commands (!help, !discord, !socials, !rules) with cooldowns.",
            category="interaction",
            capabilities=[ModuleCapability.CHAT_READ, ModuleCapability.CHAT_WRITE],
            supported_events=["CHAT_MESSAGE"],
        )
        super().__init__(metadata)

        # (stream_id, cmd_name) -> last execution timestamp
        self._command_cooldowns: Dict[Tuple[str, str], float] = {}
        # (stream_id, user_id) -> last execution timestamp
        self._user_cooldowns: Dict[Tuple[str, str], float] = {}
        self.metrics = {"commands_executed": 0, "commands_blocked_cooldown": 0}

    async def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Handle incoming CHAT_MESSAGE events."""
        if event_name != "CHAT_MESSAGE":
            return

        try:
            msg = ChatMessage(**event_data)
        except Exception:
            return

        stream_id = msg.stream_id
        from app.core.safety_controller import safety_controller
        can_cmd, _ = safety_controller.can_execute_command(stream_id)
        if not can_cmd:
            return

        config = self.get_stream_config(stream_id)
        if not config.enabled:
            return  # Disabled on this stream

        text = msg.message_text.strip()
        if not text.startswith("!"):
            return

        # Parse and normalize command name
        parts = re.split(r"\s+", text)
        cmd_name = parts[0][1:].lower()
        if not cmd_name:
            return

        commands_map = config.settings.get("custom_commands", DEFAULT_COMMANDS)
        if cmd_name not in commands_map:
            return

        # Check cooldowns (default: 5s per command, 10s per user)
        cmd_cooldown = config.settings.get("command_cooldown_sec", 5.0)
        user_cooldown = config.settings.get("user_cooldown_sec", 10.0)
        now = time.time()

        cmd_key = (stream_id, cmd_name)
        if cmd_key in self._command_cooldowns and now - self._command_cooldowns[cmd_key] < cmd_cooldown:
            self.metrics["commands_blocked_cooldown"] += 1
            return

        user_key = (stream_id, msg.author_id)
        if user_key in self._user_cooldowns and now - self._user_cooldowns[user_key] < user_cooldown:
            self.metrics["commands_blocked_cooldown"] += 1
            return

        # Record cooldowns
        self._command_cooldowns[cmd_key] = now
        self._user_cooldowns[user_key] = now

        response_text = commands_map[cmd_name]

        # Post response through YouTube stream session if available
        try:
            session = stream_manager.get_session(stream_id)
            if session and session.is_active:
                await session.send_chat_message(response_text)
            self.metrics["commands_executed"] += 1
            await event_bus.publish(
                "COMMAND_EXECUTED",
                {
                    "stream_id": stream_id,
                    "command": cmd_name,
                    "author_id": msg.author_id,
                    "response": response_text,
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to post command '{cmd_name}' reply to YouTube: {exc}")
