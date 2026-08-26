"""Virtual economy engine: XP, leveling, coins, store administration, and atomic purchases."""

import math
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChannelSettings, Purchase, StoreItem, User
from app.utils import get_logger

logger = get_logger("goddess.economy")


def calculate_level(xp: int) -> int:
    """Centralized formula: level = max(1, floor(sqrt(xp) * 0.1) + 1)."""
    if xp <= 0:
        return 1
    lvl = int(math.floor(math.sqrt(xp) * 0.1)) + 1
    return max(1, lvl)


async def get_or_create_user(
    session: AsyncSession,
    channel_id: str,
    youtube_user_id: str,
    username: str,
) -> User:
    """Fetch existing user or create a new user profile."""
    stmt = select(User).where(
        User.channel_id == channel_id,
        User.youtube_user_id == youtube_user_id,
    )
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = User(
            channel_id=channel_id,
            youtube_user_id=youtube_user_id,
            username=username,
            xp=0,
            level=1,
            coins=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        await session.flush()
    else:
        # Update username if changed
        if user.username != username:
            user.username = username
            user.updated_at = datetime.now(UTC)

    return user


async def process_message_reward(
    session: AsyncSession,
    channel_id: str,
    youtube_user_id: str,
    username: str,
    channel_settings: ChannelSettings,
    now: datetime | None = None,
) -> tuple[bool, bool, int]:
    """
    Process message activity rewards (XP + Coins).
    Returns (rewarded: bool, leveled_up: bool, new_level: int).
    """
    current_time = now or datetime.now(UTC)
    user = await get_or_create_user(session, channel_id, youtube_user_id, username)

    # Check cooldown
    if user.last_reward_at:
        elapsed = (current_time - user.last_reward_at).total_seconds()
        if elapsed < channel_settings.reward_cooldown:
            return False, False, user.level

    # Award XP and coins
    user.xp += channel_settings.xp_per_message
    user.coins += channel_settings.coins_per_message
    user.last_reward_at = current_time
    user.updated_at = current_time

    # Calculate Level
    new_level = calculate_level(user.xp)
    leveled_up = False
    if new_level > user.level:
        user.level = new_level
        leveled_up = True
        logger.info(f"User @{username} in channel {channel_id} leveled up to Level {new_level}!")

    return True, leveled_up, user.level


# ---------------------------------------------------------------------------
# Store Admin Operations
# ---------------------------------------------------------------------------


async def add_store_item(
    session: AsyncSession,
    channel_id: str,
    item_name: str,
    description: str,
    cost: int,
    created_by: str | None,
) -> tuple[bool, str]:
    """Add a new item to the channel store."""
    clean_name = item_name.strip()
    if not clean_name:
        return False, "⚠️ Item name cannot be empty."

    if cost < 0:
        return False, "⚠️ Item cost must be 0 or higher."

    # Check if item already exists
    stmt = select(StoreItem).where(
        StoreItem.channel_id == channel_id,
        func.lower(StoreItem.item_name) == clean_name.lower(),
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        if not existing.enabled:
            # Re-enable and update
            existing.enabled = True
            existing.description = description
            existing.cost = cost
            existing.updated_at = datetime.now(UTC)
            return True, f"✅ Store item '{clean_name}' re-enabled ({cost} coins)."
        return (
            False,
            f"⚠️ Store item '{clean_name}' already exists. Use !editst or !chps.",
        )

    item = StoreItem(
        channel_id=channel_id,
        item_name=clean_name,
        description=description,
        cost=cost,
        enabled=True,
        created_by=created_by,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(item)
    await session.flush()
    return True, f"✅ Store item '{clean_name}' added for {cost} coins."


async def delete_store_item(
    session: AsyncSession,
    channel_id: str,
    item_name: str,
) -> tuple[bool, str]:
    """Soft-delete a store item (preserves historical purchase records)."""
    clean_name = item_name.strip().lower()
    stmt = select(StoreItem).where(
        StoreItem.channel_id == channel_id,
        func.lower(StoreItem.item_name) == clean_name,
        StoreItem.enabled.is_(True),
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        return False, f"⚠️ Store item '{item_name}' not found."

    item.enabled = False
    item.updated_at = datetime.now(UTC)
    await session.flush()
    return True, f"✅ Store item '{item.item_name}' removed from store."


async def edit_store_item_description(
    session: AsyncSession,
    channel_id: str,
    item_name: str,
    new_description: str,
) -> tuple[bool, str]:
    """Update store item description."""
    clean_name = item_name.strip().lower()
    stmt = select(StoreItem).where(
        StoreItem.channel_id == channel_id,
        func.lower(StoreItem.item_name) == clean_name,
        StoreItem.enabled.is_(True),
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        return False, f"⚠️ Store item '{item_name}' not found."

    item.description = new_description
    item.updated_at = datetime.now(UTC)
    await session.flush()
    return True, f"✅ Store item '{item.item_name}' description updated."


async def change_store_item_price(
    session: AsyncSession,
    channel_id: str,
    item_name: str,
    new_cost: int,
) -> tuple[bool, str]:
    """Update store item price."""
    if new_cost < 0:
        return False, "⚠️ Price must be 0 or higher."

    clean_name = item_name.strip().lower()
    stmt = select(StoreItem).where(
        StoreItem.channel_id == channel_id,
        func.lower(StoreItem.item_name) == clean_name,
        StoreItem.enabled.is_(True),
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        return False, f"⚠️ Store item '{item_name}' not found."

    item.cost = new_cost
    item.updated_at = datetime.now(UTC)
    await session.flush()
    return True, f"✅ Store item '{item.item_name}' price changed to {new_cost} coins."


async def list_store_items(
    session: AsyncSession,
    channel_id: str,
) -> list[StoreItem]:
    """List active store items for a channel."""
    stmt = (
        select(StoreItem)
        .where(
            StoreItem.channel_id == channel_id,
            StoreItem.enabled.is_(True),
        )
        .order_by(StoreItem.cost.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


# ---------------------------------------------------------------------------
# Atomic Store Purchase with Double-Spend Protection
# ---------------------------------------------------------------------------


async def purchase_store_item(
    session: AsyncSession,
    channel_id: str,
    youtube_user_id: str,
    username: str,
    item_name: str,
) -> tuple[bool, str]:
    """
    Atomically process a store purchase using row-level locking.
    Prevents double-spending of coins.
    """
    clean_item_name = item_name.strip().lower()

    # 1. Fetch store item
    stmt_item = select(StoreItem).where(
        StoreItem.channel_id == channel_id,
        func.lower(StoreItem.item_name) == clean_item_name,
        StoreItem.enabled.is_(True),
    )
    res_item = await session.execute(stmt_item)
    item = res_item.scalar_one_or_none()

    if not item:
        return False, f"❌ Item '{item_name}' not found in the store."

    # 2. Fetch User with row-level lock (with_for_update)
    stmt_user = (
        select(User)
        .where(
            User.channel_id == channel_id,
            User.youtube_user_id == youtube_user_id,
        )
        .with_for_update()
    )
    res_user = await session.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    if not user:
        user = await get_or_create_user(session, channel_id, youtube_user_id, username)

    # 3. Check coin balance
    if user.coins < item.cost:
        return (
            False,
            f"❌ @{username}, you need {item.cost} coins (you have {user.coins}).",
        )

    # 4. Deduct balance and record purchase
    user.coins -= item.cost
    user.updated_at = datetime.now(UTC)

    purchase = Purchase(
        channel_id=channel_id,
        user_id=user.id,
        item_id=item.id,
        cost=item.cost,  # Record historical price paid
        created_at=datetime.now(UTC),
    )
    session.add(purchase)
    await session.flush()

    logger.info(
        f"Purchase successful: @{username} bought '{item.item_name}' for {item.cost} coins (remaining={user.coins})"
    )
    return (
        True,
        f"🎉 @{username} purchased '{item.item_name}' for {item.cost} coins! (Remaining: {user.coins} 🪙)",
    )
