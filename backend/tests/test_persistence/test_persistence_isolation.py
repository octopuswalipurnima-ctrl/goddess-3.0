"""
Tests ensuring strict multi-stream data isolation in persistence layer.
"""

import pytest
from app.db.repositories.cohost_repository import CoHostRepository
from app.db.repositories.moderation_repository import ModerationRepository
from app.db.repositories.module_repository import ModuleRepository


@pytest.mark.asyncio
async def test_multi_stream_persistence_isolation(test_db_session):
    """Verify that records for Stream A are never returned when querying Stream B."""
    mod_repo = ModerationRepository(test_db_session)
    cohost_repo = CoHostRepository(test_db_session)
    module_repo = ModuleRepository(test_db_session)

    # 1. Moderation records for Stream A and Stream B
    await mod_repo.record_audit(
        stream_id="stream_alpha",
        message_id="msg_a",
        author_id="user_a",
        author_name="UserA",
        category="SPAM",
        confidence=0.9,
        severity="LOW",
        recommended_action="DELETE",
        action_taken="DELETE",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="alpha:msg_a",
    )

    await mod_repo.record_audit(
        stream_id="stream_beta",
        message_id="msg_b",
        author_id="user_b",
        author_name="UserB",
        category="HARASSMENT",
        confidence=0.95,
        severity="HIGH",
        recommended_action="TIMEOUT",
        action_taken="TIMEOUT",
        action_status="EXECUTED",
        is_dry_run=False,
        idempotency_key="beta:msg_b",
    )

    # Verify Stream Alpha only gets Stream Alpha records
    alpha_audits = await mod_repo.list_audits_for_stream("stream_alpha")
    assert len(alpha_audits) == 1
    assert alpha_audits[0].stream_id == "stream_alpha"
    assert alpha_audits[0].author_name == "UserA"

    # Verify Stream Beta only gets Stream Beta records
    beta_audits = await mod_repo.list_audits_for_stream("stream_beta")
    assert len(beta_audits) == 1
    assert beta_audits[0].stream_id == "stream_beta"
    assert beta_audits[0].author_name == "UserB"

    # 2. Module Config Isolation
    await module_repo.set_config("commands", "stream_alpha", enabled=True, config_data={"prefix": "!"})
    await module_repo.set_config("commands", "stream_beta", enabled=False, config_data={"prefix": "?"})

    alpha_mod_cfg = await module_repo.get_config("commands", "stream_alpha")
    beta_mod_cfg = await module_repo.get_config("commands", "stream_beta")

    assert alpha_mod_cfg.enabled is True
    assert alpha_mod_cfg.config_data["prefix"] == "!"
    assert beta_mod_cfg.enabled is False
    assert beta_mod_cfg.config_data["prefix"] == "?"
