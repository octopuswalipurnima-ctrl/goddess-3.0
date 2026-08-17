"""
Tests for Zero Cross-Stream Knowledge Contamination in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.knowledge import CreatorKnowledgeManager


def test_knowledge_base_zero_cross_stream_leakage():
    """Verify Stream A facts cannot be queried or matched from Stream B or C."""
    mgr = CreatorKnowledgeManager()

    mgr.set_fact("STREAM_A", "prize", "$500 Gift Card", category="sponsor")
    mgr.set_fact("STREAM_B", "prize", "$100 Steam Code", category="sponsor")

    fact_a = mgr.get_fact("STREAM_A", "prize")
    fact_b = mgr.get_fact("STREAM_B", "prize")
    fact_c = mgr.get_fact("STREAM_C", "prize")

    assert fact_a is not None and fact_a.value == "$500 Gift Card"
    assert fact_b is not None and fact_b.value == "$100 Steam Code"
    assert fact_c is None
