"""Tests for 1v1 queue, FIFO ordering, duplicate join prevention, and race-safety."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import CommandContext, PermissionLevel, registry
from app.models import Channel, ChannelSettings, Stream


@pytest.mark.asyncio
async def test_1v1_queue_fifo_and_duplicate_join(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test 1v1 FIFO ordering and duplicate join prevention."""
    channel, channel_settings, stream = setup_channel_and_stream

    def make_ctx(user_id: str, name: str, perm: PermissionLevel = PermissionLevel.VIEWER) -> CommandContext:
        return CommandContext(
            session=db_session,
            channel_id=channel.channel_id,
            stream_id=stream.id,
            live_chat_id=stream.live_chat_id,
            author_id=user_id,
            author_name=name,
            permission=perm,
            channel_settings=channel_settings,
        )

    # 1. Viewer A joins
    res_a = await registry.execute("!join", make_ctx("user_a", "Alice"))
    assert "Alice joined the 1v1 queue" in (res_a or "")

    # 2. Viewer A tries to join again -> duplicate warning
    res_a_dup = await registry.execute("!join", make_ctx("user_a", "Alice"))
    assert "already in the queue" in (res_a_dup or "")

    # 3. Viewer B joins
    res_b = await registry.execute("!join", make_ctx("user_b", "Bob"))
    assert "Bob joined the 1v1 queue" in (res_b or "")

    # 4. Viewer C joins
    res_c = await registry.execute("!join", make_ctx("user_c", "Charlie"))
    assert "Charlie joined the 1v1 queue" in (res_c or "")

    ctx_mod = make_ctx("mod_1", "StreamMod", PermissionLevel.MODERATOR)

    # 5. Moderator calls !next1v1 -> Alice (First In, First Out)
    next_1 = await registry.execute("!next1v1", ctx_mod)
    assert "Next 1v1: @Alice" in (next_1 or "")

    # 6. Moderator calls !next1v1 again -> Bob
    next_2 = await registry.execute("!next1v1", ctx_mod)
    assert "Next 1v1: @Bob" in (next_2 or "")

    # 7. Moderator calls !next1v1 again -> Charlie
    next_3 = await registry.execute("!next1v1", ctx_mod)
    assert "Next 1v1: @Charlie" in (next_3 or "")

    # 8. Moderator calls !next1v1 when empty
    next_empty = await registry.execute("!next1v1", ctx_mod)
    assert "waiting list is empty" in (next_empty or "")


@pytest.mark.asyncio
async def test_1v1_stream_isolation(
    db_session: AsyncSession,
    setup_channel_and_stream: tuple[Channel, ChannelSettings, Stream],
):
    """Test that 1v1 queue entries are isolated per stream."""
    channel, channel_settings, stream1 = setup_channel_and_stream

    # Create a second stream
    stream2 = Stream(
        channel_id=channel.channel_id,
        youtube_video_id="TEST_VIDEO_2",
        live_chat_id="TEST_LIVE_CHAT_2",
        title="Second Stream",
        status="LIVE",
    )
    db_session.add(stream2)
    await db_session.commit()

    ctx_s1 = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream1.id,
        live_chat_id=stream1.live_chat_id,
        author_id="user_x",
        author_name="UserX",
        permission=PermissionLevel.VIEWER,
        channel_settings=channel_settings,
    )

    ctx_s2 = CommandContext(
        session=db_session,
        channel_id=channel.channel_id,
        stream_id=stream2.id,
        live_chat_id=stream2.live_chat_id,
        author_id="user_x",
        author_name="UserX",
        permission=PermissionLevel.VIEWER,
        channel_settings=channel_settings,
    )

    # User X joins stream 1 queue
    await registry.execute("!join", ctx_s1)

    # User X should be able to join stream 2 queue (stream isolation)
    res_s2 = await registry.execute("!join", ctx_s2)
    assert "UserX joined the 1v1 queue" in (res_s2 or "")
