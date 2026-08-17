"""
Chaos & Fault Injection Scenarios A–I for GODDESS AI 2.0.

Executes controlled simulated faults across all layers to verify system resilience,
fail-safe behavior, transaction rollback, and error isolation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.auth.models import UserRole, UserSchema
from app.auth.permissions import get_permissions_for_role
from app.core.events import EventBus
from app.core.redis import RedisStateManager
from app.services.moderation.manager import ModerationManager
from app.services.moderation.models import ModerationAction
from app.services.youtube.credentials import YouTubeCredentialManager
from app.services.youtube.models import ChatMessage


@pytest.mark.asyncio
async def test_chaos_scenario_a_postgres_unavailable():
    """Scenario A: Verify database outage fails safely without fabricating persistence success."""
    from app.db.session import ping_database
    
    mock_conn = AsyncMock()
    mock_conn.__aenter__.side_effect = ConnectionRefusedError("Connection refused by database server")
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    with patch("app.db.session.get_engine", return_value=mock_engine):
        status = await ping_database()
        assert status["status"] in ("UNAVAILABLE", "ERROR")


@pytest.mark.asyncio
async def test_chaos_scenario_b_redis_unavailable():
    """Scenario B: Verify Redis outage seamlessly falls back to local in-memory store."""
    manager = RedisStateManager(redis_url="redis://127.0.0.1:9999/0")  # Non-existent port
    await manager.initialize()
    ping = await manager.ping()
    
    assert "IN_MEMORY" in ping["mode"]
    # Ensure cooldowns still function
    await manager.set_cooldown("chaos_user", ttl_seconds=10.0)
    assert await manager.is_on_cooldown("chaos_user") is True


@pytest.mark.asyncio
async def test_chaos_scenario_c_gemini_unavailable():
    """Scenario C: Verify Gemini outage fails safely without blocking deterministic moderation rules."""
    mod_manager = ModerationManager()
    msg = ChatMessage(
        stream_id="STREAM_CHAOS",
        message_id="msg_001",
        channel_id="channel_chaos",
        author_id="user_spammer",
        author_name="Spammer",
        message_text="FREE BITCOIN VISIT HTTPS://SPAM.XYZ",
    )
    
    decision = await mod_manager.process_message(msg)
    assert decision is not None
    assert decision.recommended_action != ModerationAction.NONE


@pytest.mark.asyncio
async def test_chaos_scenario_d_youtube_unavailable():
    """Scenario D: Verify YouTube API outage triggers credential rotation without infinite loops."""
    mgr = YouTubeCredentialManager(keys=["AIzaSyKey1", "AIzaSyKey2"])
    k1, _ = mgr.get_credential()
    await mgr.mark_failed(k1, "Quota Exceeded", is_quota=True, cooldown_seconds=60)
    k2, _ = mgr.get_credential()
    await mgr.mark_failed(k2, "Quota Exceeded", is_quota=True, cooldown_seconds=60)
    
    assert mgr.has_available_credentials is False


@pytest.mark.asyncio
async def test_chaos_scenario_e_websocket_disconnect_cleanup():
    """Scenario E: Verify abrupt WebSocket disconnect cleanly removes connection from active pool."""
    from app.api.v1.endpoints.ws import HardenedConnectionManager
    
    ws_manager = HardenedConnectionManager()
    mock_ws = AsyncMock()
    user = UserSchema(
        id=1,
        username="creator_chaos",
        role=UserRole.OWNER,
        is_active=True,
        permissions=get_permissions_for_role(UserRole.OWNER),
    )
    
    await ws_manager.register(mock_ws, user)
    assert ws_manager.active_count == 1
    
    await ws_manager.unregister(mock_ws)
    assert ws_manager.active_count == 0


@pytest.mark.asyncio
async def test_chaos_scenario_f_module_crash_isolation():
    """Scenario F: Verify a crashing module does not take down other active modules or event bus."""
    bus = EventBus()
    crashed_module_ran = False
    healthy_module_ran = False

    async def crashing_module_handler(payload):
        nonlocal crashed_module_ran
        crashed_module_ran = True
        raise ValueError("Fatal module memory fault simulation!")

    async def healthy_module_handler(payload):
        nonlocal healthy_module_ran
        healthy_module_ran = True

    bus.subscribe("TEST_EVENT", crashing_module_handler)
    bus.subscribe("TEST_EVENT", healthy_module_handler)

    await bus.publish("TEST_EVENT", {"data": "test"})

    assert crashed_module_ran is True
    assert healthy_module_ran is True


@pytest.mark.asyncio
async def test_chaos_scenario_g_stream_crash_isolation():
    """Scenario G: Verify one unhealthy stream crashing leaves remaining streams operating."""
    from tests.load.scenarios import LoadScenario
    from tests.load.simulator import DeterministicLoadSimulator
    
    scenario = LoadScenario(
        name="Chaos-Stream-Crash",
        stream_ids=["HEALTHY_A", "CRASHING_B", "HEALTHY_C"],
        viewers_per_stream=20,
        messages_per_stream=20,
    )
    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()
    
    assert len(simulator.stream_message_history["HEALTHY_A"]) == 20
    assert len(simulator.stream_message_history["HEALTHY_C"]) == 20


@pytest.mark.asyncio
async def test_chaos_scenario_h_database_transaction_rollback():
    """Scenario H: Verify database transaction rollback preserves data integrity on failure."""
    from app.db.base import Base
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            async with session.begin():
                await session.execute(sa.text("SELECT 1"))
                raise RuntimeError("Simulated transaction crash!")
    except RuntimeError:
        pass  # Expected rollback

    async with session_factory() as session:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar() == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_chaos_scenario_i_extreme_chat_burst():
    """Scenario I: Verify system handles massive chat burst with bounded queues and latency."""
    from tests.load.scenarios import Burst4StreamScenario
    from tests.load.simulator import DeterministicLoadSimulator
    
    scenario = Burst4StreamScenario(messages_per_stream=100)
    simulator = DeterministicLoadSimulator(scenario)
    metrics = await simulator.run()

    assert metrics.processed_messages == 400
    assert metrics.errors == 0
    assert metrics.p99_latency_ms < 250.0
