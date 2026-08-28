"""Add join_message_sent column to streams table.

Revision ID: 002_add_join_message_sent
Revises: 001_initial_schema
Create Date: 2026-08-28 07:15:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.migration")

revision: str = "002_add_join_message_sent"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    logger.info("--> [1/1] Adding column 'join_message_sent' to table 'streams'...")
    op.add_column(
        "streams",
        sa.Column(
            "join_message_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    logger.info("--> Reverting column 'join_message_sent' from table 'streams'...")
    op.drop_column("streams", "join_message_sent")
