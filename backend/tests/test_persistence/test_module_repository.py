"""
Tests for ModuleRepository operations and stream-specific configurations.
"""

import pytest
from app.db.repositories.module_repository import ModuleRepository


@pytest.mark.asyncio
async def test_module_repository_config_persistence(test_db_session):
    """Test saving and retrieving module configurations per stream."""
    repo = ModuleRepository(test_db_session)

    # Configure commands module for stream_alpha
    cfg1 = await repo.set_config(
        module_id="commands",
        stream_id="stream_alpha",
        enabled=True,
        config_data={"custom_commands": {"!socials": "https://x.com/goddess"}},
    )
    assert cfg1.module_id == "commands"
    assert cfg1.enabled is True

    # Configure welcome module for stream_alpha (disabled)
    cfg2 = await repo.set_config(
        module_id="welcome",
        stream_id="stream_alpha",
        enabled=False,
        config_data={"greeting": "Welcome to the stream!"},
    )
    assert cfg2.enabled is False

    # List configs for stream_alpha
    configs = await repo.list_configs_for_stream("stream_alpha")
    assert len(configs) == 2

    # Query active
    active = await repo.list_all_active_configs()
    assert len(active) == 1
    assert active[0].module_id == "commands"
