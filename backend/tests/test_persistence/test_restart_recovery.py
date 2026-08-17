"""
Tests for RecoveryManager restoring configurations on restart without replaying old actions.
"""

import pytest
from app.db.models.cohost import CoHostConfigModel
from app.db.models.creator_settings import CreatorSettingsModel
from app.db.models.module import ModuleConfigModel
from app.db.models.stream import StreamModel
from app.db.recovery import RecoveryManager
from app.services.cohost import cohost_manager


@pytest.mark.asyncio
async def test_restart_recovery_pipeline(test_db_session):
    """Verify RecoveryManager restores persisted module and Co-Host configurations."""
    # 1. Seed database with saved configurations
    test_db_session.add(
        StreamModel(stream_id="stream_alpha", status="ACTIVE", title="Morning Stream")
    )
    test_db_session.add(
        CoHostConfigModel(
            stream_id="stream_alpha",
            enabled=True,
            personality_name="goddess_vip",
            cooldown_seconds=15.0,
            config_data={},
        )
    )
    test_db_session.add(
        ModuleConfigModel(
            module_id="commands",
            stream_id="stream_alpha",
            enabled=True,
            config_data={"prefix": "!"},
        )
    )
    test_db_session.add(
        CreatorSettingsModel(
            key="dashboard_layout",
            value_data={"compact": True},
        )
    )
    await test_db_session.commit()

    # 2. Run Recovery
    recovery = RecoveryManager(test_db_session)
    summary = await recovery.restore_all()

    assert summary["streams_restored"] == 1
    assert summary["cohost_configs_restored"] == 1
    assert summary["modules_restored"] == 1
    assert summary["settings_restored"] == 1

    # 3. Verify Co-Host manager now has restored configuration
    cfg = cohost_manager.get_config("stream_alpha")
    assert cfg.global_response_cooldown == 15.0
