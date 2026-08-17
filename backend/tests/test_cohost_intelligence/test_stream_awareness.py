"""
Tests for Stream Awareness Engine in GODDESS AI 2.0.
"""

import pytest
from app.services.cohost.awareness import StreamAwarenessEngine


def test_stream_awareness_metadata_and_prompt_formatting():
    """Verify StreamAwarenessEngine maintains stream-scoped activity and bounds events."""
    engine = StreamAwarenessEngine()

    engine.update_awareness("STREAM_A", {
        "current_activity": "Ranked Valorant",
        "category": "Gaming",
        "custom_facts": {"current_rank": "Diamond 2"},
    })

    # Add 7 moderation events (should bound to 5)
    for i in range(7):
        engine.record_moderation_event("STREAM_A", f"Banned spammer {i}")

    aw_a = engine.get_awareness("STREAM_A")
    assert aw_a.current_activity == "Ranked Valorant"
    assert len(aw_a.recent_moderation_events) == 5

    prompt_a = engine.build_awareness_prompt("STREAM_A")
    assert "Ranked Valorant" in prompt_a
    assert "Diamond 2" in prompt_a

    # Stream B must remain unconfigured
    aw_b = engine.get_awareness("STREAM_B")
    assert aw_b.current_activity == "Live Streaming"
    assert len(aw_b.recent_moderation_events) == 0
