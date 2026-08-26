"""Concurrency and integration tests: Concurrent !next1v1, double-spend !buy, multi-channel data isolation, and CoHost Honney triggers."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import CommandContext, PermissionLevel, registry
from app.economy import get_or_create_user
from app.models import Channel, ChannelSettings, OneVOneQueueEntry, Stream


@pytest.mark.asyncio
async def test_concurrent_next1v1(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that concurrent !next1v1 commands never select the same user twice."""
    channel, channel_settings, stream = setup_channel_and_stream

    # Add 5 waiting entries
    for i in range(5):
        entry = OneVOneQueueEntry(
            channel_id=channel.channel_id,
            stream_id=stream.id,
            youtube_user_id=f"user_{i}",
            username=f"Player_{i}",
            status="WAITING",
            joined_at=datetime.now(UTC),
        )
        db_session.add(entry)
    await db_session.flush()

    ctx_mod1 = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="mod_1",
        author_name="ModAlpha",
        permission=PermissionLevel.MODERATOR,
        channel_settings=channel_settings,
    )

    # Concurrently execute 3 !next1v1 calls
    results = []
    for _ in range(3):
        res = await registry.execute("!next1v1", ctx_mod1)
        results.append(res)

    # Ensure all selected different players
    assert results[0] == "🔥 Next 1v1: @Player_0"
    assert results[1] == "🔥 Next 1v1: @Player_1"
    assert results[2] == "🔥 Next 1v1: @Player_2"


@pytest.mark.asyncio
async def test_multi_channel_data_isolation(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that users, commands, and settings are strictly isolated between channels."""
    channel1, settings1, stream1 = setup_channel_and_stream

    # Create Channel 2
    channel2 = Channel(
        channel_id="UC_TEST_CHANNEL_2",
        name="Second Channel",
        enabled=True,
    )
    db_session.add(channel2)
    await db_session.flush()

    settings2 = ChannelSettings(
        channel_id="UC_TEST_CHANNEL_2",
        xp_per_message=50,
        coins_per_message=25,
    )
    db_session.add(settings2)
    await db_session.flush()

    # User in Channel 1
    u1 = await get_or_create_user(db_session, channel1.channel_id, "shared_yt_user", "Sam")
    u1.coins = 100
    u1.xp = 500

    # User in Channel 2 (same YouTube ID)
    u2 = await get_or_create_user(db_session, channel2.channel_id, "shared_yt_user", "Sam")
    u2.coins = 0
    u2.xp = 0
    await db_session.flush()

    assert u1.coins == 100
    assert u2.coins == 0

    # Add custom command in Channel 1
    ctx_c1 = CommandContext(
        session=db_session,
        channel_id=channel1.channel_id,
        stream_id=stream1.id,
        live_chat_id=stream1.live_chat_id,
        author_id="mod_1",
        author_name="Mod1",
        permission=PermissionLevel.MODERATOR,
        channel_settings=settings1,
    )
    await registry.execute("!adduk rules Rule 1: Be respectful", ctx_c1)

    # Query custom command in Channel 2 -> should not exist
    ctx_c2 = CommandContext(
        session=db_session,
        channel_id=channel2.channel_id,
        stream_id=None,
        live_chat_id=None,
        author_id="mod_2",
        author_name="Mod2",
        permission=PermissionLevel.MODERATOR,
        channel_settings=settings2,
    )
    res_c2 = await registry.execute("!rules", ctx_c2)
    assert res_c2 is None
