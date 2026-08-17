"""
Tests for 200-Character Response Length Constraint in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.response_generator import ResponseGenerator


def test_sanitize_response_strictly_caps_at_two_hundred_chars():
    """Verify response generator cleanly truncates responses over 200 characters."""
    gen = ResponseGenerator()

    very_long_text = "This is a super long AI response that just goes on and on with unnecessary chatter and verbose explanations that exceed the strict live chat character limits for streaming. " * 3
    sanitized = gen._sanitize_response(very_long_text, max_length=200)

    assert len(sanitized) <= 200
    assert sanitized.endswith("...")
