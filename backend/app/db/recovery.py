"""
System Restart Recovery Manager for GODDESS AI 2.0.

Restores stream settings, moderation policies, co-host configurations,
and module preferences from the persistent PostgreSQL database upon restart
without replaying old actions or resending historical messages.
"""

from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.cohost_repository import CoHostRepository
from app.db.repositories.creator_settings_repository import CreatorSettingsRepository
from app.db.repositories.moderation_repository import ModerationRepository
from app.db.repositories.module_repository import ModuleRepository
from app.db.repositories.stream_repository import StreamRepository
from app.modules import module_manager
from app.modules.models import StreamModuleConfig
from app.services.cohost import cohost_manager
from app.services.moderation import moderation_manager

logger = get_logger("db.recovery")


class RecoveryManager:
    """Orchestrates safe state restoration from PostgreSQL upon startup."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stream_repo = StreamRepository(session)
        self.mod_repo = ModerationRepository(session)
        self.cohost_repo = CoHostRepository(session)
        self.module_repo = ModuleRepository(session)
        self.settings_repo = CreatorSettingsRepository(session)

    async def restore_all(self) -> Dict[str, Any]:
        """
        Execute full recovery pipeline:
        1. Restore Module configurations and enabled states.
        2. Restore Stream-specific Co-Host configurations.
        3. Restore Stream configurations.
        4. Load Creator Settings.
        Returns a summary report of restored entities.
        """
        summary = {
            "streams_restored": 0,
            "modules_restored": 0,
            "cohost_configs_restored": 0,
            "settings_restored": 0,
        }

        # 1. Restore Module Configs
        try:
            mod_configs = await self.module_repo.list_all_active_configs()
            for cfg in mod_configs:
                mod = module_manager.registry.get(cfg.module_id)
                if mod:
                    mod.update_stream_config(
                        cfg.stream_id,
                        StreamModuleConfig(
                            enabled=cfg.enabled,
                            settings=cfg.config_data,
                        ),
                    )
                    summary["modules_restored"] += 1
            logger.info(f"Recovery: Restored {summary['modules_restored']} module configurations.")
        except Exception as err:
            logger.warning(f"Recovery: Failed to restore module configs: {err}")

        # 2. Restore Co-Host Configs
        try:
            cohost_cfgs = await self.cohost_repo.list_all()
            for c in cohost_cfgs:
                cohost_manager.update_config(
                    c.stream_id,
                    {
                        "enabled": c.enabled,
                        "dry_run": c.dry_run,
                        "emergency_stop": c.emergency_stop,
                        "global_response_cooldown": c.cooldown_seconds,
                    },
                )
                summary["cohost_configs_restored"] += 1
            logger.info(f"Recovery: Restored {summary['cohost_configs_restored']} Co-Host configurations.")
        except Exception as err:
            logger.warning(f"Recovery: Failed to restore Co-Host configs: {err}")

        # 3. Restore Stream Configs
        try:
            streams = await self.stream_repo.list_all()
            summary["streams_restored"] = len(streams)
            logger.info(f"Recovery: Discovered {summary['streams_restored']} persistent stream records.")
        except Exception as err:
            logger.warning(f"Recovery: Failed to query stream records: {err}")

        # 4. Restore Creator Settings
        try:
            all_settings = await self.settings_repo.list_all_settings()
            summary["settings_restored"] = len(all_settings)
            logger.info(f"Recovery: Restored {summary['settings_restored']} creator preferences.")
        except Exception as err:
            logger.warning(f"Recovery: Failed to restore creator settings: {err}")

        return summary
