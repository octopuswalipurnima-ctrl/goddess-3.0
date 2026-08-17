"""
Tests for 4-Stream Personality Isolation across STREAM_A, STREAM_B, STREAM_C, STREAM_D.
"""

import pytest
from app.services.cohost.personality import CoHostPersonalityManager


def test_four_stream_personality_complete_isolation():
    """Verify distinct personalities across all 4 streams without cross-talk."""
    mgr = CoHostPersonalityManager()

    mgr.update_personality("STREAM_A", {"name": "Aria", "tone": "friendly", "energy_level": "high"})
    mgr.update_personality("STREAM_B", {"name": "Blitz", "tone": "energetic", "energy_level": "high"})
    mgr.update_personality("STREAM_C", {"name": "Cipher", "tone": "professional", "energy_level": "low"})
    mgr.update_personality("STREAM_D", {"name": "Dash", "tone": "humorous", "energy_level": "medium"})

    assert mgr.get_personality("STREAM_A").name == "Aria"
    assert mgr.get_personality("STREAM_B").name == "Blitz"
    assert mgr.get_personality("STREAM_C").name == "Cipher"
    assert mgr.get_personality("STREAM_D").name == "Dash"
