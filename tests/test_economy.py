"""Tests for economy, leveling, coins, store administration, and atomic purchases."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import CommandContext, PermissionLevel, registry
from app.economy import calculate_level, process_message_reward
from app.models import Channel, ChannelSettings, Purchase, Stream, User


def test_level_formula():
    """Verify centralized level formula."""
    assert calculate_level(0) == 1
    assert calculate_level(50) == 1
    assert calculate_level(100) == 2
    assert calculate_level(400) == 3
    assert calculate_level(900) == 4
    assert calculate_level(10000) == 11


@pytest.mark.asyncio
async def test_economy_reward_and_cooldown(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test XP and coins reward and 60-second cooldown enforcement."""
    channel, channel_settings, stream = setup_channel_and_stream
    now = datetime.now(UTC)

    # 1. First message rewards XP and coins
    rewarded, leveled_up, lvl = await process_message_reward(
        session=db_session,
        channel_id=channel.channel_id,
        youtube_user_id="user_123",
        username="Gamer1",
        channel_settings=channel_settings,
        now=now,
    )
    assert rewarded is True
    assert lvl == 1

    # Check user balance
    stmt = select(User).where(User.youtube_user_id == "user_123")
    res = await db_session.execute(stmt)
    user = res.scalar_one()
    assert user.xp == 10
    assert user.coins == 5

    # 2. Second message 10 seconds later -> rejected by cooldown
    rewarded2, _, _ = await process_message_reward(
        session=db_session,
        channel_id=channel.channel_id,
        youtube_user_id="user_123",
        username="Gamer1",
        channel_settings=channel_settings,
        now=now + timedelta(seconds=10),
    )
    assert rewarded2 is False

    # 3. Third message 65 seconds later -> rewarded
    rewarded3, _, _ = await process_message_reward(
        session=db_session,
        channel_id=channel.channel_id,
        youtube_user_id="user_123",
        username="Gamer1",
        channel_settings=channel_settings,
        now=now + timedelta(seconds=65),
    )
    assert rewarded3 is True
    assert user.xp == 20
    assert user.coins == 10


@pytest.mark.asyncio
async def test_store_admin_and_purchase(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test adding item to store, checking balance, and purchasing."""
    channel, channel_settings, stream = setup_channel_and_stream

    ctx_mod = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="mod_1",
        author_name="SuperMod",
        permission=PermissionLevel.MODERATOR,
        channel_settings=channel_settings,
    )

    ctx_viewer = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream.id,
        live_chat_id=stream.live_chat_id,
        author_id="buyer_1",
        author_name="RichViewer",
        permission=PermissionLevel.VIEWER,
        channel_settings=channel_settings,
    )

    # 1. Admin adds VIP item
    res_add = await registry.execute("!addst VIP 50 Special VIP role", ctx_mod)
    assert "added for 50 coins" in (res_add or "")

    # 2. Viewer tries to buy with 0 coins -> fail
    res_buy_fail = await registry.execute("!buy VIP", ctx_viewer)
    assert "need 50 coins" in (res_buy_fail or "")

    # 3. Give user 100 coins
    stmt = select(User).where(User.youtube_user_id == "buyer_1")
    res_u = await db_session.execute(stmt)
    user = res_u.scalar_one()
    user.coins = 100
    await db_session.commit()

    # 4. Viewer buys VIP item -> success
    res_buy_ok = await registry.execute("!buy VIP", ctx_viewer)
    assert "purchased 'VIP' for 50 coins" in (res_buy_ok or "")
    assert "Remaining: 50" in (res_buy_ok or "")

    # 5. Check Purchase record
    stmt_p = select(Purchase).where(Purchase.user_id == user.id)
    res_p = await db_session.execute(stmt_p)
    purchase = res_p.scalar_one()
    assert purchase.cost == 50
