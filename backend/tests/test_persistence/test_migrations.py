"""
Tests for Alembic migration metadata and configuration.
"""

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest


def test_alembic_config_and_scripts():
    """Verify Alembic configuration and migration script discovery."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "0001_initial"


def test_migration_revisions():
    """Verify the migration chain."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    rev = script.get_revision("0001_initial")
    assert rev is not None
    assert rev.down_revision is None
    assert "initial" in rev.doc.lower()
