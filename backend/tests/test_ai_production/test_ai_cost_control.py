"""
Tests for AI Cost Control & Token Budget Accounting in GODDESS AI 2.0.
"""

from app.services.ai.decision_engine import AIDecisionEngine


def test_ai_request_and_token_budget_enforcement():
    """Verify daily request and token budgets are strictly enforced and fail closed."""
    engine = AIDecisionEngine()
    engine.update_stream_config(
        "STREAM_BUDGET",
        {
            "daily_request_budget": 5,
            "daily_token_budget": 500,
        },
    )

    # First 5 requests under budget
    for _ in range(5):
        allowed = engine.check_and_increment_budget("STREAM_BUDGET", estimated_tokens=50)
        assert allowed is True

    # 6th request should exceed budget
    exceeded = engine.check_and_increment_budget("STREAM_BUDGET", estimated_tokens=50)
    assert exceeded is False
    assert engine.budget_exceeded_count >= 1
