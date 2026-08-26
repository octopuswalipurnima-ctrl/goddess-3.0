"""Tests for Gemini API key pool rotation, error backoff, and structured moderation."""

import pytest

from app.gemini import (
    GeminiAPIUnavailableError,
    GeminiKeyPool,
    ModerationResult,
)
from app.utils import extract_json_from_llm_response


@pytest.mark.asyncio
async def test_gemini_key_pool_round_robin():
    """Test that key pool selects keys in round-robin sequence."""
    keys = ["key-alpha", "key-beta", "key-gamma", "key-delta"]
    pool = GeminiKeyPool(keys)

    assert pool.total_keys == 4
    assert pool.get_healthy_count() == 4

    l1, k1 = await pool.get_next_key()
    l2, k2 = await pool.get_next_key()
    l3, k3 = await pool.get_next_key()
    l4, k4 = await pool.get_next_key()
    l5, k5 = await pool.get_next_key()

    assert l1 == "gemini-key-1" and k1 == "key-alpha"
    assert l2 == "gemini-key-2" and k2 == "key-beta"
    assert l3 == "gemini-key-3" and k3 == "key-gamma"
    assert l4 == "gemini-key-4" and k4 == "key-delta"
    assert l5 == "gemini-key-1" and k5 == "key-alpha"


@pytest.mark.asyncio
async def test_gemini_key_pool_429_rotation():
    """Test that 429 errors place keys in cooldown and rotate to available healthy keys."""
    keys = ["key-1", "key-2", "key-3", "key-4"]
    pool = GeminiKeyPool(keys)

    # Key 1 receives 429
    await pool.report_failure("gemini-key-1", 429, "Resource exhausted / Quota exceeded")

    assert pool.get_healthy_count() == 3

    # Next call should select key 2
    label2, _k2 = await pool.get_next_key()
    assert label2 == "gemini-key-2"

    # Key 2 receives 429
    await pool.report_failure("gemini-key-2", 429, "Rate limited")
    assert pool.get_healthy_count() == 2

    label3, _k3 = await pool.get_next_key()
    assert label3 == "gemini-key-3"


@pytest.mark.asyncio
async def test_gemini_key_pool_all_exhausted():
    """Test that GeminiAPIUnavailableError is raised when all keys are in cooldown."""
    keys = ["key-1", "key-2"]
    pool = GeminiKeyPool(keys)

    await pool.report_failure("gemini-key-1", 429, "Rate limit")
    await pool.report_failure("gemini-key-2", 429, "Rate limit")

    assert pool.get_healthy_count() == 0

    with pytest.raises(GeminiAPIUnavailableError):
        await pool.get_next_key()


def test_moderation_result_validation():
    """Test Pydantic validation and normalization of Gemini moderation output."""
    # Percentage to float conversion
    res = ModerationResult(
        is_violation=True,
        category="toxicity",
        confidence=95.0,  # Percentage format
        severity="high",
        reason="Severe toxicity",
        needs_review=False,
    )
    assert res.confidence == 0.95
    assert res.category == "TOXICITY"
    assert res.is_violation is True

    # Standard float
    res2 = ModerationResult(
        is_violation=False,
        category="safe",
        confidence=0.15,
        severity="low",
        reason="Friendly gaming banter",
        needs_review=False,
    )
    assert res2.confidence == 0.15
    assert res2.category == "SAFE"
    assert res2.is_violation is False


def test_extract_json_from_llm_markdown():
    """Test extraction of JSON from markdown code blocks and raw strings."""
    raw_markdown = """```json
    {
      "is_violation": false,
      "category": "SAFE",
      "confidence": 0.12,
      "severity": "low",
      "reason": "Safe message",
      "needs_review": false
    }
    ```"""
    data = extract_json_from_llm_response(raw_markdown)
    assert data is not None
    assert data["is_violation"] is False
    assert data["category"] == "SAFE"
    assert data["confidence"] == 0.12
