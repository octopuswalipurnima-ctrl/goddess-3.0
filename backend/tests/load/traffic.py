"""
Traffic Pattern Generator for Multi-Stream Simulation.

Generates realistic chat message payloads conforming to YouTube Chat event structures
across distinct profiles (normal, burst, moderation-heavy, cohost-heavy, command-heavy, churn, duplicates).
"""

from dataclasses import dataclass
from enum import Enum
import random
import time
from typing import Any, Dict, List, Optional

from tests.load.viewers import SimulatedViewer, ViewerPool


class TrafficProfile(str, Enum):
    NORMAL = "NORMAL"
    BURST = "BURST"
    MODERATION_HEAVY = "MODERATION_HEAVY"
    COHOST_HEAVY = "COHOST_HEAVY"
    COMMAND_HEAVY = "COMMAND_HEAVY"
    CHURN = "CHURN"
    DUPLICATE = "DUPLICATE"
    MIXED = "MIXED"


@dataclass
class SimulatedMessage:
    """Represents a structured synthetic chat message."""
    stream_id: str
    viewer_id: str
    author_name: str
    message_id: str
    timestamp_iso: str
    timestamp_epoch: float
    text: str
    event_type: str = "CHAT_MESSAGE"
    is_mod: bool = False
    is_owner: bool = False

    def to_chat_message(self) -> Any:
        """Format as YouTube ChatMessage model."""
        from app.services.youtube.models import ChatMessage
        return ChatMessage(
            stream_id=self.stream_id,
            message_id=self.message_id,
            channel_id=f"channel_{self.stream_id}",
            author_id=self.viewer_id,
            author_name=self.author_name,
            message_text=self.text,
            published_at=self.timestamp_iso,
            is_chat_owner=self.is_owner,
            is_chat_moderator=self.is_mod,
        )

    def to_event_payload(self) -> Dict[str, Any]:
        """Format as EventBus CHAT_MESSAGE payload."""
        return self.to_chat_message().model_dump()


# Sample message banks
NORMAL_MESSAGES = [
    "Hello everyone! Excited for the stream!",
    "Great gameplay today!",
    "What build are you using right now?",
    "GG that was an amazing play!",
    "Welcome to all the new viewers in chat!",
    "Haha that was so funny!",
    "Can you explain that last combo?",
    "Love the energy on this stream!",
    "Let's goooo!",
    "Don't forget to like the stream everyone!",
]

MODERATION_SPAM_MESSAGES = [
    "CLICK HERE FOR FREE BITCOIN HTTP://FREE-CRYPTO-SCAM.XYZ",
    "CHECK OUT MY CHANNEL AT HTTPS://YOUTUBE.COM/SPAMMER123",
    "BUY CHEAP FOLLOWERS AT WWW.GETFOLLOWERSNOW.ONLINE",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "ALL CAPS RAGE COMMENT THIS IS SO LOUD AND ANNOYING",
    "YOU SUCK BANNED_WORD_TEST GO AWAY",
    "FREE GIFT CARDS VISIT HTTPS://CLAIM-PRIZE.TOP",
    "SPAM SPAM SPAM SPAM SPAM SPAM SPAM SPAM SPAM SPAM",
]

COHOST_MESSAGES = [
    "@goddess what strategy should we use next round?",
    "@goddess who is your favorite character in this game?",
    "@goddess can you give a shoutout to the new subscribers?",
    "@goddess what are your thoughts on this boss fight?",
    "@goddess tell us a fun gaming fact!",
    "Hey @goddess how are you doing today?",
]

COMMAND_MESSAGES = [
    "!ping",
    "!help",
    "!stats",
    "!rules",
    "!schedule",
    "!socials",
]


class TrafficGenerator:
    """Generates synthetic messages based on configured profile and viewer pools."""

    def __init__(self, stream_id: str, viewer_pool: ViewerPool, seed: int = 100):
        self.stream_id = stream_id
        self.viewer_pool = viewer_pool
        self.rng = random.Random(seed)
        self._message_counter = 0

    def generate_message(self, profile: TrafficProfile = TrafficProfile.NORMAL) -> SimulatedMessage:
        """Produce a single deterministic message matching the target profile."""
        self._message_counter += 1
        msg_id = f"msg_{self.stream_id}_{self._message_counter:06d}"
        now_epoch = time.time()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch))

        # Select viewer
        viewer = self.viewer_pool.get_random_viewer()
        viewer.message_count += 1
        viewer.last_message_time_s = now_epoch

        # Generate message text by profile
        text = self._generate_text_for_profile(profile, viewer)

        return SimulatedMessage(
            stream_id=self.stream_id,
            viewer_id=viewer.viewer_id,
            author_name=viewer.name,
            message_id=msg_id,
            timestamp_iso=now_iso,
            timestamp_epoch=now_epoch,
            text=text,
            is_mod=viewer.is_mod,
            is_owner=viewer.is_owner,
        )

    def _generate_text_for_profile(self, profile: TrafficProfile, viewer: SimulatedViewer) -> str:
        if profile == TrafficProfile.NORMAL:
            return self.rng.choice(NORMAL_MESSAGES)
        elif profile == TrafficProfile.MODERATION_HEAVY:
            # 70% spam/toxic/link, 30% normal
            if self.rng.random() < 0.70:
                return self.rng.choice(MODERATION_SPAM_MESSAGES)
            return self.rng.choice(NORMAL_MESSAGES)
        elif profile == TrafficProfile.COHOST_HEAVY:
            # 80% @goddess mentions, 20% normal
            if self.rng.random() < 0.80:
                return self.rng.choice(COHOST_MESSAGES)
            return self.rng.choice(NORMAL_MESSAGES)
        elif profile == TrafficProfile.COMMAND_HEAVY:
            # 75% commands, 25% normal
            if self.rng.random() < 0.75:
                return self.rng.choice(COMMAND_MESSAGES)
            return self.rng.choice(NORMAL_MESSAGES)
        elif profile == TrafficProfile.DUPLICATE:
            # Repeated identical message
            return "Repeated burst message for duplicate flood test!"
        elif profile == TrafficProfile.BURST:
            return self.rng.choice(NORMAL_MESSAGES)
        elif profile == TrafficProfile.CHURN:
            return f"Hello I just joined stream {self.stream_id}!"
        else:  # MIXED
            roll = self.rng.random()
            if roll < 0.40:
                return self.rng.choice(NORMAL_MESSAGES)
            elif roll < 0.60:
                return self.rng.choice(COMMAND_MESSAGES)
            elif roll < 0.80:
                return self.rng.choice(COHOST_MESSAGES)
            else:
                return self.rng.choice(MODERATION_SPAM_MESSAGES)
