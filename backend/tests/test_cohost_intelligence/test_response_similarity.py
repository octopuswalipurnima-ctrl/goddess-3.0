"""
Tests for Lexical Similarity Detection in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.deduplication import ResponseDeduplicator


def test_jaccard_similarity_trigger():
    """Verify responses with high token overlap are flagged as similar."""
    dedup = ResponseDeduplicator(history_size=30)

    dedup.record_response("STREAM_A", "Hey Alice, welcome to today's live gaming stream!")

    # Candidate with heavy overlap
    cand = "Hey Bob, welcome to today's live gaming stream!"
    is_sim, sim_score = dedup.is_similar("STREAM_A", cand, threshold=0.65)

    assert is_sim is True
    assert sim_score >= 0.65

    # Completely distinct message
    distinct = "The next tournament begins on Friday night."
    is_sim_distinct, sim_dist = dedup.is_similar("STREAM_A", distinct, threshold=0.65)
    assert is_sim_distinct is False
    assert sim_dist < 0.30
