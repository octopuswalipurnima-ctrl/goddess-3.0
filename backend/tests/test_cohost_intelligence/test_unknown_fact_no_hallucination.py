"""
Tests for Anti-Hallucination and Unknown Fact Protections in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.knowledge import CreatorKnowledgeManager


def test_unknown_fact_prompt_instructions_prohibit_guessing():
    """Verify prompt generated for unconfigured stream includes explicit anti-guessing directive."""
    mgr = CreatorKnowledgeManager()

    # Empty knowledge for Stream A
    prompt = mgr.build_knowledge_prompt("STREAM_A")
    assert "No creator facts configured" in prompt
    assert "say you don't know" in prompt
