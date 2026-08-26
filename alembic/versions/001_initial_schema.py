"""Initial migration: Create all tables for Goddess AI 3.0.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-26 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. channels
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column(
            "name",
            sa.String(length=128),
            nullable=False,
            server_default="YouTube Channel",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channels_channel_id", "channels", ["channel_id"], unique=True)

    # 2. channel_settings
    op.create_table(
        "channel_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "cohost_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "moderation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "moderation_mode",
            sa.String(length=32),
            nullable=False,
            server_default="balanced",
        ),
        sa.Column("moderation_threshold", sa.Float(), nullable=False, server_default="0.90"),
        sa.Column(
            "personality",
            sa.String(length=64),
            nullable=False,
            server_default="friendly",
        ),
        sa.Column("xp_per_message", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("coins_per_message", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("reward_cooldown", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("cohost_cooldown", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("context_message_count", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.channel_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_channel_settings_channel_id",
        "channel_settings",
        ["channel_id"],
        unique=True,
    )

    # 3. users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("youtube_user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False, server_default="Viewer"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reward_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "youtube_user_id", name="uq_user_channel_ytuser"),
    )
    op.create_index(
        "ix_user_channel_ytuser",
        "users",
        ["channel_id", "youtube_user_id"],
        unique=False,
    )
    op.create_index("ix_users_channel_id", "users", ["channel_id"], unique=False)
    op.create_index("ix_users_youtube_user_id", "users", ["youtube_user_id"], unique=False)

    # 4. streams
    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=64), nullable=False),
        sa.Column("live_chat_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OFFLINE"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "youtube_video_id", name="uq_stream_channel_video"),
    )
    op.create_index("ix_streams_channel_id", "streams", ["channel_id"], unique=False)
    op.create_index("ix_streams_youtube_video_id", "streams", ["youtube_video_id"], unique=False)
    op.create_index("ix_streams_live_chat_id", "streams", ["live_chat_id"], unique=False)

    # 5. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=True),
        sa.Column("youtube_message_id", sa.String(length=128), nullable=False),
        sa.Column("youtube_user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("normalized_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_message_id"),
    )
    op.create_index(
        "ix_chat_messages_channel_stream_created",
        "chat_messages",
        ["channel_id", "stream_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_youtube_message_id",
        "chat_messages",
        ["youtube_message_id"],
        unique=True,
    )
    op.create_index(
        "ix_chat_messages_youtube_user_id",
        "chat_messages",
        ["youtube_user_id"],
        unique=False,
    )

    # 6. commands
    op.create_table(
        "commands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "name", name="uq_command_channel_name"),
    )
    op.create_index("ix_commands_channel_id", "commands", ["channel_id"], unique=False)
    op.create_index("ix_commands_name", "commands", ["name"], unique=False)

    # 7. store_items
    op.create_table(
        "store_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "item_name", name="uq_store_item_channel_name"),
    )
    op.create_index("ix_store_items_channel_id", "store_items", ["channel_id"], unique=False)
    op.create_index("ix_store_items_item_name", "store_items", ["item_name"], unique=False)

    # 8. purchases
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["item_id"], ["store_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_channel_id", "purchases", ["channel_id"], unique=False)
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"], unique=False)

    # 9. one_v_one_queue
    op.create_table(
        "one_v_one_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("youtube_user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="WAITING"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_by", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_queue_channel_stream_status_joined",
        "one_v_one_queue",
        ["channel_id", "stream_id", "status", "joined_at"],
        unique=False,
    )

    # 10. moderation_reviews
    op.create_table(
        "moderation_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=True),
        sa.Column("youtube_message_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("original_message", sa.Text(), nullable=False),
        sa.Column("normalized_message", sa.Text(), nullable=False),
        sa.Column("model_category", sa.String(length=64), nullable=False),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("model_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mod_reviews_channel_status_created",
        "moderation_reviews",
        ["channel_id", "status", "created_at"],
        unique=False,
    )

    # 11. moderation_memory
    op.create_table(
        "moderation_memory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("phrase", sa.String(length=256), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("is_allowed", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="SAFE"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mod_memory_channel_phrase",
        "moderation_memory",
        ["channel_id", "phrase"],
        unique=False,
    )

    # 12. websub_subscriptions
    op.create_table(
        "websub_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("lease_expiration", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_renewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_websub_subscriptions_channel_id",
        "websub_subscriptions",
        ["channel_id"],
        unique=True,
    )

    # 13. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.String(length=64), nullable=False),
        sa.Column("actor_username", sa.String(length=128), nullable=False),
        sa.Column("command", sa.String(length=64), nullable=False),
        sa.Column("safe_arguments", sa.Text(), nullable=True),
        sa.Column("target_user_id", sa.String(length=64), nullable=True),
        sa.Column("target_username", sa.String(length=128), nullable=True),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_channel_created",
        "audit_logs",
        ["channel_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("websub_subscriptions")
    op.drop_table("moderation_memory")
    op.drop_table("moderation_reviews")
    op.drop_table("one_v_one_queue")
    op.drop_table("purchases")
    op.drop_table("store_items")
    op.drop_table("commands")
    op.drop_table("chat_messages")
    op.drop_table("streams")
    op.drop_table("users")
    op.drop_table("channel_settings")
    op.drop_table("channels")
