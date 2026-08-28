"""Command parser, permission matrix, custom commands, 1v1 queue, and chat settings."""

import contextlib
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy import (
    add_store_item,
    change_store_item_price,
    delete_store_item,
    edit_store_item_description,
    get_or_create_user,
    list_store_items,
    purchase_store_item,
)
from app.models import (
    AuditLog,
    ChannelSettings,
    ChatMessage,
    Command,
    OneVOneQueueEntry,
)
from app.moderation import resolve_moderation_review
from app.utils import get_logger
from app.youtube import YouTubeClient

logger = get_logger("goddess.commands")


class PermissionLevel(IntEnum):
    VIEWER = 0
    MODERATOR = 1
    BROADCASTER = 2


RESERVED_COMMANDS = {
    "!adduk",
    "!deluk",
    "!edituk",
    "!reptuk",
    "!ghelp",
    "!help",
    "!join",
    "!next1v1",
    "!coins",
    "!rank",
    "!store",
    "!buy",
    "!addst",
    "!delst",
    "!editst",
    "!chps",
    "!delmsg",
    "!tout",
    "!hid",
    "!mod",
    "!settings",
    "!setai",
    "!setcohost",
    "!setmod",
    "!setpersonality",
    "!setxp",
    "!setcoins",
    "!setcooldown",
    "!scanlive",
}


def get_user_permission(author_details: dict[str, Any] | None) -> PermissionLevel:
    """Determine permission level from YouTube author details."""
    if not author_details:
        return PermissionLevel.VIEWER

    if author_details.get("isChatOwner", False):
        return PermissionLevel.BROADCASTER
    if author_details.get("isChatModerator", False):
        return PermissionLevel.MODERATOR
    return PermissionLevel.VIEWER


class CommandContext:
    """Context object passed to command execution handlers."""

    def __init__(
        self,
        session: AsyncSession,
        channel_id: str,
        stream_id: int | None,
        live_chat_id: str | None,
        author_id: str,
        author_name: str,
        permission: PermissionLevel,
        channel_settings: ChannelSettings,
        youtube_client: YouTubeClient | None = None,
    ) -> None:
        self.session = session
        self.channel_id = channel_id
        self.stream_id = stream_id
        self.live_chat_id = live_chat_id
        self.author_id = author_id
        self.author_name = author_name
        self.permission = permission
        self.settings = channel_settings
        self.youtube = youtube_client


class CommandRegistry:
    """Central registry and dispatcher for all Goddess AI 3.0 chat commands."""

    def __init__(self) -> None:
        self._handlers: dict[
            str,
            tuple[Callable[..., Coroutine[Any, Any, str]], PermissionLevel, str, str],
        ] = {}

    def register(
        self,
        name: str,
        permission: PermissionLevel,
        description: str,
        usage: str,
    ) -> Callable[..., Any]:
        """Decorator to register a command handler."""

        def decorator(
            func: Callable[..., Coroutine[Any, Any, str]],
        ) -> Callable[..., Coroutine[Any, Any, str]]:
            cmd_norm = name.lower().strip()
            self._handlers[cmd_norm] = (func, permission, description, usage)
            return func

        return decorator

    async def execute(
        self,
        raw_text: str,
        ctx: CommandContext,
    ) -> str | None:
        """Parse and execute a chat command if text starts with '!'."""
        if not raw_text or not raw_text.startswith("!"):
            return None

        # Clean command and arguments
        parts = raw_text.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        args_text = parts[1].strip() if len(parts) > 1 else ""

        # 1. Built-in command
        if cmd_name in self._handlers:
            handler, req_perm, desc, usage = self._handlers[cmd_name]
            if ctx.permission < req_perm:
                logger.warning(
                    f"Permission denied for @{ctx.author_name} (perm={ctx.permission}) calling {cmd_name}"
                )
                return "⛔ You don't have permission to use this command."

            try:
                result = await handler(ctx, args_text)
                # Audit log privileged actions
                if req_perm >= PermissionLevel.MODERATOR:
                    await self._log_audit(ctx, cmd_name, args_text, result)
                return result
            except Exception as e:
                logger.error(f"Error executing command {cmd_name}: {e}")
                return "⚠️ An error occurred while executing that command."

        # 2. Custom Command Lookup
        custom_resp = await self._execute_custom_command(ctx, cmd_name)
        if custom_resp:
            return custom_resp

        return None

    async def _execute_custom_command(self, ctx: CommandContext, cmd_name: str) -> str | None:
        """Check database for custom commands created via !adduk."""
        stmt = select(Command).where(
            Command.channel_id == ctx.channel_id,
            Command.name == cmd_name,
        )
        res = await ctx.session.execute(stmt)
        cmd = res.scalar_one_or_none()
        if cmd:
            return cmd.response
        return None

    async def _log_audit(
        self,
        ctx: CommandContext,
        command: str,
        safe_arguments: str,
        result: str,
    ) -> None:
        """Record privileged commands in AuditLog."""
        log = AuditLog(
            channel_id=ctx.channel_id,
            stream_id=ctx.stream_id,
            actor_user_id=ctx.author_id,
            actor_username=ctx.author_name,
            command=command,
            safe_arguments=safe_arguments[:250] if safe_arguments else None,
            result="SUCCESS" if not result.startswith(("⚠️", "⛔", "❌")) else "FAILED",
            created_at=datetime.now(UTC),
        )
        ctx.session.add(log)


registry = CommandRegistry()

# ---------------------------------------------------------------------------
# 1. Custom Commands Management (!adduk, !deluk, !Edituk, !reptuk)
# ---------------------------------------------------------------------------


@registry.register(
    name="!adduk",
    permission=PermissionLevel.MODERATOR,
    description="Add a custom command",
    usage="!adduk <command> <response>",
)
async def cmd_adduk(ctx: CommandContext, args: str) -> str:
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "⚠️ Usage: !adduk <command> <response>"

    raw_cmd, response = parts[0], parts[1].strip()
    cmd_name = raw_cmd if raw_cmd.startswith("!") else f"!{raw_cmd}"
    cmd_norm = cmd_name.lower().strip()

    if cmd_norm in RESERVED_COMMANDS:
        return f"⚠️ '{cmd_name}' is a reserved system command and cannot be overwritten."

    # Check if already exists
    stmt = select(Command).where(
        Command.channel_id == ctx.channel_id,
        Command.name == cmd_norm,
    )
    res = await ctx.session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        return f"⚠️ Command {cmd_name} already exists. Use !Edituk to update."

    cmd = Command(
        channel_id=ctx.channel_id,
        name=cmd_norm,
        response=response,
        created_by=ctx.author_name,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    ctx.session.add(cmd)
    await ctx.session.flush()
    return f"✅ Command {cmd_name} added."


@registry.register(
    name="!deluk",
    permission=PermissionLevel.MODERATOR,
    description="Delete a custom command",
    usage="!deluk <command>",
)
async def cmd_deluk(ctx: CommandContext, args: str) -> str:
    if not args.strip():
        return "⚠️ Usage: !deluk <command>"

    raw_cmd = args.strip().split()[0]
    cmd_name = raw_cmd if raw_cmd.startswith("!") else f"!{raw_cmd}"
    cmd_norm = cmd_name.lower().strip()

    if cmd_norm in RESERVED_COMMANDS:
        return f"⚠️ Cannot delete system command '{cmd_name}'."

    stmt = select(Command).where(
        Command.channel_id == ctx.channel_id,
        Command.name == cmd_norm,
    )
    res = await ctx.session.execute(stmt)
    cmd = res.scalar_one_or_none()

    if not cmd:
        return f"⚠️ Custom command {cmd_name} not found."

    await ctx.session.delete(cmd)
    await ctx.session.flush()
    return f"✅ Command {cmd_name} deleted."


@registry.register(
    name="!edituk",
    permission=PermissionLevel.MODERATOR,
    description="Edit an existing custom command",
    usage="!Edituk <command> <new response>",
)
async def cmd_edituk(ctx: CommandContext, args: str) -> str:
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "⚠️ Usage: !Edituk <command> <new response>"

    raw_cmd, new_response = parts[0], parts[1].strip()
    cmd_name = raw_cmd if raw_cmd.startswith("!") else f"!{raw_cmd}"
    cmd_norm = cmd_name.lower().strip()

    stmt = select(Command).where(
        Command.channel_id == ctx.channel_id,
        Command.name == cmd_norm,
    )
    res = await ctx.session.execute(stmt)
    cmd = res.scalar_one_or_none()

    if not cmd:
        return f"⚠️ Custom command {cmd_name} not found. Use !adduk to create it."

    cmd.response = new_response
    cmd.updated_at = datetime.now(UTC)
    await ctx.session.flush()
    return f"✅ Command {cmd_name} updated."


@registry.register(
    name="!reptuk",
    permission=PermissionLevel.MODERATOR,
    description="Repeat/test a stored custom command",
    usage="!reptuk <command>",
)
async def cmd_reptuk(ctx: CommandContext, args: str) -> str:
    if not args.strip():
        return "⚠️ Usage: !reptuk <command>"

    raw_cmd = args.strip().split()[0]
    cmd_name = raw_cmd if raw_cmd.startswith("!") else f"!{raw_cmd}"
    cmd_norm = cmd_name.lower().strip()

    stmt = select(Command).where(
        Command.channel_id == ctx.channel_id,
        Command.name == cmd_norm,
    )
    res = await ctx.session.execute(stmt)
    cmd = res.scalar_one_or_none()

    if not cmd:
        return f"⚠️ Custom command {cmd_name} not found."

    return f"📢 {cmd.name}: {cmd.response}"


# ---------------------------------------------------------------------------
# 2. 1v1 Waiting Queue (!join, !next1v1)
# ---------------------------------------------------------------------------


@registry.register(
    name="!join",
    permission=PermissionLevel.VIEWER,
    description="Join the active 1v1 waiting queue",
    usage="!join",
)
async def cmd_join(ctx: CommandContext, args: str) -> str:
    if not ctx.stream_id:
        return "⚠️ No active live stream found for the 1v1 queue."

    # Check if already in queue with WAITING status
    stmt = select(OneVOneQueueEntry).where(
        OneVOneQueueEntry.channel_id == ctx.channel_id,
        OneVOneQueueEntry.stream_id == ctx.stream_id,
        OneVOneQueueEntry.youtube_user_id == ctx.author_id,
        OneVOneQueueEntry.status == "WAITING",
    )
    res = await ctx.session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        return f"⚠️ @{ctx.author_name}, you're already in the queue."

    entry = OneVOneQueueEntry(
        channel_id=ctx.channel_id,
        stream_id=ctx.stream_id,
        youtube_user_id=ctx.author_id,
        username=ctx.author_name,
        status="WAITING",
        joined_at=datetime.now(UTC),
    )
    ctx.session.add(entry)
    await ctx.session.flush()
    return f"🎮 @{ctx.author_name} joined the 1v1 queue!"


@registry.register(
    name="!next1v1",
    permission=PermissionLevel.MODERATOR,
    description="Select next player from 1v1 waiting list (FIFO)",
    usage="!next1v1",
)
async def cmd_next1v1(ctx: CommandContext, args: str) -> str:
    if not ctx.stream_id:
        return "⚠️ No active live stream found."

    # Atomically select oldest WAITING entry with row-level lock
    stmt = (
        select(OneVOneQueueEntry)
        .where(
            OneVOneQueueEntry.channel_id == ctx.channel_id,
            OneVOneQueueEntry.stream_id == ctx.stream_id,
            OneVOneQueueEntry.status == "WAITING",
        )
        .order_by(OneVOneQueueEntry.joined_at.asc())
        .with_for_update()
        .limit(1)
    )
    res = await ctx.session.execute(stmt)
    entry = res.scalar_one_or_none()

    if not entry:
        return "⚠️ 1v1 waiting list is empty."

    entry.status = "SELECTED"
    entry.selected_at = datetime.now(UTC)
    entry.selected_by = ctx.author_name
    await ctx.session.flush()

    return f"🔥 Next 1v1: @{entry.username}"


# ---------------------------------------------------------------------------
# 3. Economy & Store Commands (!coins, !rank, !store, !buy)
# ---------------------------------------------------------------------------


@registry.register(
    name="!coins",
    permission=PermissionLevel.VIEWER,
    description="Check your coins balance and level",
    usage="!coins",
)
async def cmd_coins(ctx: CommandContext, args: str) -> str:
    user = await get_or_create_user(ctx.session, ctx.channel_id, ctx.author_id, ctx.author_name)
    return f"🪙 @{user.username} has {user.coins} coins (Level {user.level} | {user.xp} XP)."


@registry.register(
    name="!rank",
    permission=PermissionLevel.VIEWER,
    description="View your rank, XP, level, and coins",
    usage="!rank",
)
async def cmd_rank(ctx: CommandContext, args: str) -> str:
    user = await get_or_create_user(ctx.session, ctx.channel_id, ctx.author_id, ctx.author_name)
    return f"🏆 @{user.username} — Level {user.level} | XP {user.xp} | 🪙 {user.coins} coins"


@registry.register(
    name="!store",
    permission=PermissionLevel.VIEWER,
    description="View available items in the virtual store",
    usage="!store",
)
async def cmd_store(ctx: CommandContext, args: str) -> str:
    items = await list_store_items(ctx.session, ctx.channel_id)
    if not items:
        return "🛒 The store is currently empty."

    item_strs = [f"📦 {it.item_name} ({it.cost} 🪙) - {it.description}" for it in items[:5]]
    return "🛒 Store Items: " + " | ".join(item_strs)


@registry.register(
    name="!buy",
    permission=PermissionLevel.VIEWER,
    description="Purchase an item from the virtual store",
    usage="!buy <item_name>",
)
async def cmd_buy(ctx: CommandContext, args: str) -> str:
    item_name = args.strip()
    if not item_name:
        return "⚠️ Usage: !buy <item_name>"

    success, msg = await purchase_store_item(
        session=ctx.session,
        channel_id=ctx.channel_id,
        youtube_user_id=ctx.author_id,
        username=ctx.author_name,
        item_name=item_name,
    )
    return msg


# ---------------------------------------------------------------------------
# 4. Store Admin Commands (!addst, !delst, !editst, !chps)
# ---------------------------------------------------------------------------


@registry.register(
    name="!addst",
    permission=PermissionLevel.MODERATOR,
    description="Add an item to the store",
    usage="!addst <item_name> <price> <description>",
)
async def cmd_addst(ctx: CommandContext, args: str) -> str:
    parts = args.split(maxsplit=2)
    if len(parts) < 3:
        return "⚠️ Usage: !addst <item_name> <price> <description>"

    name, price_str, description = parts[0], parts[1], parts[2]
    try:
        price = int(price_str)
    except ValueError:
        return "⚠️ Price must be an integer."

    success, msg = await add_store_item(
        session=ctx.session,
        channel_id=ctx.channel_id,
        item_name=name,
        description=description,
        cost=price,
        created_by=ctx.author_name,
    )
    return msg


@registry.register(
    name="!delst",
    permission=PermissionLevel.MODERATOR,
    description="Remove an item from the store",
    usage="!delst <item_name>",
)
async def cmd_delst(ctx: CommandContext, args: str) -> str:
    name = args.strip()
    if not name:
        return "⚠️ Usage: !delst <item_name>"

    success, msg = await delete_store_item(ctx.session, ctx.channel_id, name)
    return msg


@registry.register(
    name="!editst",
    permission=PermissionLevel.MODERATOR,
    description="Edit item description in the store",
    usage="!editst <item_name> <new description>",
)
async def cmd_editst(ctx: CommandContext, args: str) -> str:
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        return "⚠️ Usage: !editst <item_name> <new description>"

    name, new_desc = parts[0], parts[1]
    success, msg = await edit_store_item_description(ctx.session, ctx.channel_id, name, new_desc)
    return msg


@registry.register(
    name="!chps",
    permission=PermissionLevel.MODERATOR,
    description="Change item price in the store",
    usage="!chps <item_name> <new_price>",
)
async def cmd_chps(ctx: CommandContext, args: str) -> str:
    parts = args.split()
    if len(parts) < 2:
        return "⚠️ Usage: !chps <item_name> <new_price>"

    name, price_str = parts[0], parts[1]
    try:
        new_price = int(price_str)
    except ValueError:
        return "⚠️ Price must be an integer."

    success, msg = await change_store_item_price(ctx.session, ctx.channel_id, name, new_price)
    return msg


# ---------------------------------------------------------------------------
# 5. Moderation Commands (!delmsg, !tout, !hid, !mod)
# ---------------------------------------------------------------------------


@registry.register(
    name="!delmsg",
    permission=PermissionLevel.MODERATOR,
    description="Delete latest message from user in active stream",
    usage="!delmsg @username",
)
async def cmd_delmsg(ctx: CommandContext, args: str) -> str:
    target = args.strip().lstrip("@")
    if not target:
        return "⚠️ Usage: !delmsg @username"

    # Find latest message from this username/user_id in active stream
    stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.channel_id == ctx.channel_id,
            func.lower(ChatMessage.username) == target.lower(),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    res = await ctx.session.execute(stmt)
    latest_msg = res.scalar_one_or_none()

    if not latest_msg:
        return f"⚠️ No recent message found for @{target}."

    if not ctx.youtube:
        return "⚠️ YouTube integration client unavailable."

    success = await ctx.youtube.delete_chat_message(latest_msg.youtube_message_id)
    if success:
        return f"🗑️ Last message from @{target} deleted."
    return f"⚠️ Could not delete message for @{target}. Check bot permissions."


@registry.register(
    name="!tout",
    permission=PermissionLevel.MODERATOR,
    description="Timeout a user from live chat",
    usage="!tout @username [duration_seconds]",
)
async def cmd_tout(ctx: CommandContext, args: str) -> str:
    parts = args.split()
    if not parts:
        return "⚠️ Usage: !tout @username [seconds]"

    target_name = parts[0].lstrip("@")
    duration = 300
    if len(parts) > 1:
        with contextlib.suppress(ValueError):
            duration = max(10, min(86400, int(parts[1])))

    # Resolve target user_id
    stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.channel_id == ctx.channel_id,
            func.lower(ChatMessage.username) == target_name.lower(),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    res = await ctx.session.execute(stmt)
    latest_msg = res.scalar_one_or_none()

    if not latest_msg or not ctx.live_chat_id or not ctx.youtube:
        return f"⚠️ Unable to resolve live chat info for @{target_name}."

    success = await ctx.youtube.timeout_user(
        live_chat_id=ctx.live_chat_id,
        youtube_user_id=latest_msg.youtube_user_id,
        duration_seconds=duration,
    )
    if success:
        return f"⏱️ @{target_name} timed out for {duration}s."
    return "⚠️ I couldn't complete that moderation action."


@registry.register(
    name="!hid",
    permission=PermissionLevel.BROADCASTER,
    description="Permanently hide user from channel",
    usage="!hid @username",
)
async def cmd_hid(ctx: CommandContext, args: str) -> str:
    target_name = args.strip().lstrip("@")
    if not target_name:
        return "⚠️ Usage: !hid @username"

    stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.channel_id == ctx.channel_id,
            func.lower(ChatMessage.username) == target_name.lower(),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    res = await ctx.session.execute(stmt)
    latest_msg = res.scalar_one_or_none()

    if not latest_msg or not ctx.live_chat_id or not ctx.youtube:
        return f"⚠️ Unable to resolve live chat info for @{target_name}."

    success = await ctx.youtube.hide_user(
        live_chat_id=ctx.live_chat_id,
        youtube_user_id=latest_msg.youtube_user_id,
    )
    if success:
        return f"🚫 @{target_name} has been hidden from the channel."
    return "⚠️ I couldn't complete that action."


@registry.register(
    name="!mod",
    permission=PermissionLevel.MODERATOR,
    description="Resolve human-in-the-loop moderation reviews",
    usage="!mod <allow|ban|ignore> <review_id>",
)
async def cmd_mod(ctx: CommandContext, args: str) -> str:
    parts = args.split()
    if len(parts) < 2:
        return "⚠️ Usage: !mod <allow|ban|ignore> <review_id>"

    action, id_str = parts[0], parts[1]
    try:
        review_id = int(id_str)
    except ValueError:
        return "⚠️ Review ID must be an integer."

    success, msg = await resolve_moderation_review(
        session=ctx.session,
        channel_id=ctx.channel_id,
        review_id=review_id,
        action=action,
        reviewed_by=ctx.author_name,
        youtube_client=ctx.youtube,
    )
    return msg


# ---------------------------------------------------------------------------
# 6. Chat Settings Commands (!settings, !setai, !setcohost, etc.)
# ---------------------------------------------------------------------------


@registry.register(
    name="!settings",
    permission=PermissionLevel.MODERATOR,
    description="Show current channel settings",
    usage="!settings",
)
async def cmd_settings(ctx: CommandContext, args: str) -> str:
    s = ctx.settings
    ai_status = "ON" if s.ai_enabled else "OFF"
    cohost_status = "ON" if s.cohost_enabled else "OFF"
    return (
        f"⚙️ AI: {ai_status} | CoHost: {cohost_status} | "
        f"🛡️ Mod: {s.moderation_mode.upper()} | "
        f"⭐ XP: {s.xp_per_message} | 🪙 Coins: {s.coins_per_message} | ⏱️ CD: {s.reward_cooldown}s"
    )


@registry.register(
    name="!setai",
    permission=PermissionLevel.MODERATOR,
    description="Enable or disable AI moderation",
    usage="!setai on|off",
)
async def cmd_setai(ctx: CommandContext, args: str) -> str:
    val = args.strip().lower()
    if val in ("on", "true", "1", "enable"):
        ctx.settings.ai_enabled = True
        return "✅ AI moderation enabled."
    elif val in ("off", "false", "0", "disable"):
        ctx.settings.ai_enabled = False
        return "✅ AI moderation disabled."
    return "⚠️ Usage: !setai on|off"


@registry.register(
    name="!setcohost",
    permission=PermissionLevel.MODERATOR,
    description="Enable or disable Honney AI Co-Host",
    usage="!setcohost on|off",
)
async def cmd_setcohost(ctx: CommandContext, args: str) -> str:
    val = args.strip().lower()
    if val in ("on", "true", "1", "enable"):
        ctx.settings.cohost_enabled = True
        return "✅ Honney Co-Host enabled."
    elif val in ("off", "false", "0", "disable"):
        ctx.settings.cohost_enabled = False
        return "✅ Honney Co-Host disabled."
    return "⚠️ Usage: !setcohost on|off"


@registry.register(
    name="!setmod",
    permission=PermissionLevel.MODERATOR,
    description="Set moderation strictness mode",
    usage="!setmod relaxed|balanced|strict",
)
async def cmd_setmod(ctx: CommandContext, args: str) -> str:
    val = args.strip().lower()
    if val in ("relaxed", "balanced", "strict"):
        ctx.settings.moderation_mode = val
        return f"✅ Moderation mode set to {val.upper()}."
    return "⚠️ Usage: !setmod relaxed|balanced|strict"


@registry.register(
    name="!setpersonality",
    permission=PermissionLevel.MODERATOR,
    description="Set Honney personality style",
    usage="!setpersonality <style>",
)
async def cmd_setpersonality(ctx: CommandContext, args: str) -> str:
    val = args.strip()
    if not val:
        return "⚠️ Usage: !setpersonality <style>"
    ctx.settings.personality = val[:60]
    return f"✅ Honney personality set to: {val[:60]}"


@registry.register(
    name="!setxp",
    permission=PermissionLevel.MODERATOR,
    description="Set XP rewarded per chat message",
    usage="!setxp <amount>",
)
async def cmd_setxp(ctx: CommandContext, args: str) -> str:
    try:
        val = int(args.strip())
        if val < 0:
            return "⚠️ XP amount must be >= 0."
        ctx.settings.xp_per_message = val
        return f"✅ XP per message set to {val}."
    except ValueError:
        return "⚠️ Usage: !setxp <amount>"


@registry.register(
    name="!setcoins",
    permission=PermissionLevel.MODERATOR,
    description="Set coins rewarded per chat message",
    usage="!setcoins <amount>",
)
async def cmd_setcoins(ctx: CommandContext, args: str) -> str:
    try:
        val = int(args.strip())
        if val < 0:
            return "⚠️ Coins amount must be >= 0."
        ctx.settings.coins_per_message = val
        return f"✅ Coins per message set to {val}."
    except ValueError:
        return "⚠️ Usage: !setcoins <amount>"


@registry.register(
    name="!setcooldown",
    permission=PermissionLevel.MODERATOR,
    description="Set reward cooldown seconds",
    usage="!setcooldown <seconds>",
)
async def cmd_setcooldown(ctx: CommandContext, args: str) -> str:
    try:
        val = int(args.strip())
        if val < 5:
            return "⚠️ Cooldown must be at least 5 seconds."
        ctx.settings.reward_cooldown = val
        return f"✅ Reward cooldown set to {val}s."
    except ValueError:
        return "⚠️ Usage: !setcooldown <seconds>"


@registry.register(
    name="!scanlive",
    permission=PermissionLevel.MODERATOR,
    description="Manually scan configured channel for active live stream",
    usage="!scanlive",
)
async def cmd_scanlive(ctx: CommandContext, args: str) -> str:
    """Scan channel for active broadcast and connect."""
    target_channel_id = ctx.channel_id
    if not ctx.youtube:
        return "🍯 Honney: Misayuislive is currently OFFLINE."

    try:
        live_info = await ctx.youtube.get_active_live_video(target_channel_id)
        if live_info:
            return "🍯 Honney: Live detected! Connecting to chat..."
        return "🍯 Honney: Misayuislive is currently OFFLINE."
    except Exception as e:
        logger.error(f"Error executing !scanlive for channel {target_channel_id}: {e}")
        return "🍯 Honney: Misayuislive is currently OFFLINE."


# ---------------------------------------------------------------------------
# 7. Dynamic Help (!ghelp)
# ---------------------------------------------------------------------------


@registry.register(
    name="!ghelp",
    permission=PermissionLevel.VIEWER,
    description="Show available commands",
    usage="!ghelp",
)
async def cmd_ghelp(ctx: CommandContext, args: str) -> str:
    viewer_cmds = [
        "1v1: !join",
        "Economy: !coins, !rank, !store, !buy <item>",
        "Co-Host: type 'honney' in chat",
    ]

    mod_cmds = [
        "Queue: !next1v1",
        "Custom: !adduk, !deluk, !Edituk, !reptuk",
        "Store: !addst, !delst, !editst, !chps",
        "Mod: !delmsg, !tout, !hid, !mod allow/ban",
        "Settings: !settings, !setai, !setmod, !setxp",
    ]

    if ctx.permission >= PermissionLevel.MODERATOR:
        return "🛡️ MOD COMMANDS: " + " | ".join(mod_cmds)
    return "✨ COMMANDS: " + " | ".join(viewer_cmds)
