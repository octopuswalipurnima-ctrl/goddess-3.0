"""
Tests for Creator Knowledge Base in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.knowledge import CreatorKnowledgeManager


def test_creator_knowledge_crud_and_query_matching():
    """Verify CreatorKnowledgeManager stores and matches facts by stream."""
    mgr = CreatorKnowledgeManager()

    mgr.set_fact("STREAM_A", "schedule", "Mon/Wed/Fri at 7 PM EST", category="schedule")
    mgr.set_fact("STREAM_A", "discord", "https://discord.gg/streamer", category="socials")

    # Match query
    matches = mgr.find_relevant_facts("STREAM_A", "What is the stream schedule?")
    assert len(matches) >= 1
    assert matches[0].key == "schedule"
    assert "7 PM EST" in matches[0].value

    prompt = mgr.build_knowledge_prompt("STREAM_A")
    assert "SCHEDULE" in prompt
    assert "Mon/Wed/Fri at 7 PM EST" in prompt

    # Delete fact
    deleted = mgr.delete_fact("STREAM_A", "schedule")
    assert deleted is True
    assert mgr.get_fact("STREAM_A", "schedule") is None
