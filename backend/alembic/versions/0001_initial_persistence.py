"""0001_initial_persistence

Revision ID: 0001_initial
Revises: 
Create Date: 2026-08-17 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Streams Table
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INITIALIZING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_streams_stream_id", "streams", ["stream_id"], unique=True)
    op.create_index("ix_streams_channel_id", "streams", ["channel_id"], unique=False)
    op.create_index("ix_streams_status", "streams", ["status"], unique=False)
    op.create_index("ix_streams_channel_status", "streams", ["channel_id", "status"], unique=False)

    # 2. Stream Configs Table
    op.create_table(
        "stream_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stream_configs_stream_id", "stream_configs", ["stream_id"], unique=True)

    # 3. Moderation Audit Records Table
    op.create_table(
        "moderation_audit_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("author_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("recommended_action", sa.String(length=64), nullable=False, server_default="NONE"),
        sa.Column("action_taken", sa.String(length=64), nullable=False, server_default="NONE"),
        sa.Column("action_status", sa.String(length=32), nullable=False, server_default="APPROVED"),
        sa.Column("is_dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_id", "message_id", "action_taken", name="uq_mod_audit_stream_msg_action"),
    )
    op.create_index("ix_moderation_audit_records_stream_id", "moderation_audit_records", ["stream_id"], unique=False)
    op.create_index("ix_moderation_audit_records_message_id", "moderation_audit_records", ["message_id"], unique=False)
    op.create_index("ix_moderation_audit_records_author_id", "moderation_audit_records", ["author_id"], unique=False)
    op.create_index("ix_moderation_audit_records_category", "moderation_audit_records", ["category"], unique=False)
    op.create_index("ix_moderation_audit_records_action_status", "moderation_audit_records", ["action_status"], unique=False)
    op.create_index("ix_moderation_audit_records_idempotency_key", "moderation_audit_records", ["idempotency_key"], unique=True)
    op.create_index("ix_moderation_audit_records_timestamp", "moderation_audit_records", ["timestamp"], unique=False)
    op.create_index("ix_mod_audit_stream_time", "moderation_audit_records", ["stream_id", "timestamp"], unique=False)
    op.create_index("ix_mod_audit_stream_category", "moderation_audit_records", ["stream_id", "category"], unique=False)

    # 4. Co-Host Configs Table
    op.create_table(
        "cohost_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("emergency_stop", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("personality_name", sa.String(length=64), nullable=False, server_default="goddess"),
        sa.Column("cooldown_seconds", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("config_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cohost_configs_stream_id", "cohost_configs", ["stream_id"], unique=True)

    # 5. Co-Host Audit Records Table
    op.create_table(
        "cohost_audit_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("author_name", sa.String(length=128), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=False),
        sa.Column("intent_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("response_text", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SENT"),
        sa.Column("is_dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cohost_audit_records_stream_id", "cohost_audit_records", ["stream_id"], unique=False)
    op.create_index("ix_cohost_audit_records_message_id", "cohost_audit_records", ["message_id"], unique=False)
    op.create_index("ix_cohost_audit_records_intent", "cohost_audit_records", ["intent"], unique=False)
    op.create_index("ix_cohost_audit_records_status", "cohost_audit_records", ["status"], unique=False)
    op.create_index("ix_cohost_audit_records_idempotency_key", "cohost_audit_records", ["idempotency_key"], unique=True)
    op.create_index("ix_cohost_audit_records_timestamp", "cohost_audit_records", ["timestamp"], unique=False)
    op.create_index("ix_cohost_audit_stream_time", "cohost_audit_records", ["stream_id", "timestamp"], unique=False)

    # 6. Module Configs Table
    op.create_table(
        "module_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_id", "stream_id", name="uq_module_stream_config"),
    )
    op.create_index("ix_module_configs_module_id", "module_configs", ["module_id"], unique=False)
    op.create_index("ix_module_configs_stream_id", "module_configs", ["stream_id"], unique=False)
    op.create_index("ix_module_configs_stream", "module_configs", ["stream_id", "module_id"], unique=False)

    # 7. Creator Settings Table
    op.create_table(
        "creator_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_settings_key", "creator_settings", ["key"], unique=True)


def downgrade() -> None:
    op.drop_table("creator_settings")
    op.drop_table("module_configs")
    op.drop_table("cohost_audit_records")
    op.drop_table("cohost_configs")
    op.drop_table("moderation_audit_records")
    op.drop_table("stream_configs")
    op.drop_table("streams")
