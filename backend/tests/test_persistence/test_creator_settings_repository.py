"""
Tests for CreatorSettingsRepository key-value preference storage.
"""

import pytest
from app.db.repositories.creator_settings_repository import CreatorSettingsRepository


@pytest.mark.asyncio
async def test_creator_settings_repository_crud(test_db_session):
    """Test saving and retrieving creator settings dicts."""
    repo = CreatorSettingsRepository(test_db_session)

    # 1. Set setting
    await repo.set_setting(
        key="theme_preference",
        value_data={"dark_mode": True, "accent_color": "cyan"},
    )

    # 2. Get setting
    setting = await repo.get_setting("theme_preference")
    assert setting["dark_mode"] is True
    assert setting["accent_color"] == "cyan"

    # 3. Default fallback
    missing = await repo.get_setting("non_existent_key", default={"val": 42})
    assert missing["val"] == 42
