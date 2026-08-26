"""Tests for command parsing, permissions, custom commands, and chat settings."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import CommandContext, PermissionLevel, registry
from app.models import Channel, ChannelSettings, Stream


@pytest.mark.asyncio
async def test_custom_command_lifecycle(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test full lifecycle of !adduk, execution, !Edituk, !reptuk, and !deluk."""
    channel, channel_settings, stream = setup_channel_and_stream

    ctx_mod = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="mod_user_1",
        author_name="SuperMod",
        permission=PermissionLevel.MODERATOR,
        channel_settings=channel_settings,
    )

    ctx_viewer = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="viewer_1",
        author_name="ViewerBob",
        permission=PermissionLevel.VIEWER,
        channel_settings=channel_settings,
    )

    # 1. Add command !discord
    res = await registry.execute("!adduk discord Join our Discord: discord.gg/test", ctx_mod)
    assert res == "✅ Command !discord added."

    # 2. Viewer executes !discord
    res_v = await registry.execute("!discord", ctx_viewer)
    assert res_v == "Join our Discord: discord.gg/test"

    # 3. Test !reptuk
    res_rep = await registry.execute("!reptuk discord", ctx_mod)
    assert "discord.gg/test" in (res_rep or "")

    # 4. Edit command !Edituk
    res_edit = await registry.execute("!Edituk discord Updated Discord link: discord.gg/new", ctx_mod)
    assert res_edit == "✅ Command !discord updated."

    # 5. Verify updated execution
    res_v2 = await registry.execute("!discord", ctx_viewer)
    assert res_v2 == "Updated Discord link: discord.gg/new"

    # 6. Delete command !deluk
    res_del = await registry.execute("!deluk discord", ctx_mod)
    assert res_del == "✅ Command !discord deleted."

    # 7. Verify command is gone
    res_gone = await registry.execute("!discord", ctx_viewer)
    assert res_gone is None


@pytest.mark.asyncio
async def test_reserved_command_protection(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that reserved system commands cannot be overwritten or deleted."""
    channel, channel_settings, stream = setup_channel_and_stream

    ctx_mod = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="mod_user_1",
        author_name="SuperMod",
        permission=PermissionLevel.MODERATOR,
        channel_settings=channel_settings,
    )

    res = await registry.execute("!adduk coins Fake Coins Command", ctx_mod)
    assert "reserved system command" in (res or "")

    res_del = await registry.execute("!deluk join", ctx_mod)
    assert "Cannot delete system command" in (res_del or "")


@pytest.mark.asyncio
async def test_permission_denied_for_viewers(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that viewers cannot execute moderator/admin commands."""
    channel, channel_settings, stream = setup_channel_and_stream

    ctx_viewer = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="viewer_1",
        author_name="ViewerBob",
        permission=PermissionLevel.VIEWER,
        channel_settings=channel_settings,
    )

    res = await registry.execute("!adduk test Hello", ctx_viewer)
    assert "permission" in (res or "").lower()

    res_settings = await registry.execute("!setai off", ctx_viewer)
    assert "permission" in (res_settings or "").lower()


@pytest.mark.asyncio
async def test_chat_settings_commands(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test updating channel settings via chat commands."""
    channel, channel_settings, stream = setup_channel_and_stream

    ctx_mod = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="mod_user_1",
        author_name="SuperMod",
        permission=PermissionLevel.MODERATOR,
        channel_settings=channel_settings,
    )

    res_ai = await registry.execute("!setai off", ctx_mod)
    assert "disabled" in (res_ai or "")
    assert channel_settings.ai_enabled is False

    res_mod = await registry.execute("!setmod strict", ctx_mod)
    assert "STRICT" in (res_mod or "")
    assert channel_settings.moderation_mode == "strict"

    res_xp = await registry.execute("!setxp 25", ctx_mod)
    assert "25" in (res_xp or "")
    assert channel_settings.xp_per_message == 25

    res_summary = await registry.execute("!settings", ctx_mod)
    assert "STRICT" in (res_summary or "")
    assert "25" in (res_summary or "")
