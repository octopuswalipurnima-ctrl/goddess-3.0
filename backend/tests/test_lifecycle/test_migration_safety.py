"""
Tests for Migration Version Safety and Compatibility.
"""

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest


def test_migration_chain_integrity():
    """Verify the complete Alembic migration sequence (0001 -> 0002)."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "0002_add_users"

    rev2 = script.get_revision("0002_add_users")
    assert rev2 is not None
    assert rev2.down_revision == "0001_initial"

    rev1 = script.get_revision("0001_initial")
    assert rev1 is not None
    assert rev1.down_revision is None
