"""
Deterministic Load Simulator Engine for GODDESS AI 2.0.

Executes offline multi-stream simulations without connecting to real YouTube or Gemini APIs.
Drives realistic traffic through EventBus, Moderation, Co-Host, and Module pipelines,
measuring latency, throughput, error rates, and verifying hard multi-stream isolation.
"""

import asyncio
import time
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, patch

from app.core.events import event_bus
from app.services.cohost.manager import cohost_manager
from app.services.gemini.manager import gemini_manager
from app.services.gemini.models import AIResponse, AIResponseStatus
from app.services.moderation.manager import moderation_manager
from app.services.moderation.models import ModerationAction
from tests.load.metrics import LoadMetrics, LoadMetricsCollector
from tests.load.scenarios import LoadScenario
from tests.load.traffic import SimulatedMessage, TrafficGenerator
from tests.load.viewers import ViewerPool


class DeterministicLoadSimulator:
    """Orchestrates deterministic multi-stream load simulations."""

    def __init__(self, scenario: LoadScenario):
        self.scenario = scenario
        self.metrics_collector = LoadMetricsCollector()
        self.viewer_pools: Dict[str, ViewerPool] = {}
        self.traffic_generators: Dict[str, TrafficGenerator] = {}
        
        # Track stream message history for isolation verification
        self.stream_message_history: Dict[str, List[str]] = {s: [] for s in scenario.stream_ids}
        self.isolation_violations: int = 0
        self.emergency_violations: int = 0
        
        self._setup()

    def _setup(self) -> None:
        """Initialize viewer pools and traffic generators per stream."""
        for idx, stream_id in enumerate(self.scenario.stream_ids):
            seed = self.scenario.random_seed + idx * 100
            pool = ViewerPool(stream_id=stream_id, count=self.scenario.viewers_per_stream, seed=seed)
            self.viewer_pools[stream_id] = pool
            self.traffic_generators[stream_id] = TrafficGenerator(
                stream_id=stream_id,
                viewer_pool=pool,
                seed=seed + 50,
            )

    async def run(self) -> LoadMetrics:
        """
        Execute the configured scenario across all streams concurrently.
        """
        mock_ai_resp = AIResponse(
            request_id="mock_req_load",
            stream_id="STREAM_A",
            status=AIResponseStatus.SUCCESS,
            text="Hey there! Thanks for tuning in to the stream!",
            model="gemini-2.5-flash",
            latency_ms=1.2,
        )

        with patch.object(gemini_manager, "request", new=AsyncMock(return_value=mock_ai_resp)):
            stream_tasks = [
                self._run_stream_simulation(stream_id)
                for stream_id in self.scenario.stream_ids
            ]
            await asyncio.gather(*stream_tasks)
            
        return self.metrics_collector.finish()

    async def _run_stream_simulation(self, stream_id: str) -> None:
        """Simulate message flow for an individual stream."""
        generator = self.traffic_generators[stream_id]
        
        for _ in range(self.scenario.messages_per_stream):
            msg: SimulatedMessage = generator.generate_message(self.scenario.profile)
            
            # Isolation check: Verify viewer belongs to this stream
            if not msg.viewer_id.startswith(f"user_{stream_id}_"):
                self.isolation_violations += 1

            start_t = time.perf_counter()
            blocked = False
            
            try:
                # 1. Publish to EventBus
                payload = msg.to_event_payload()
                await event_bus.publish("CHAT_MESSAGE", payload)
                self.metrics_collector.record_event_bus(1)
                chat_msg = msg.to_chat_message()
                
                # 2. Evaluate via Moderation Engine
                decision = await moderation_manager.process_message(chat_msg)
                
                if decision and decision.recommended_action not in (ModerationAction.NONE, ModerationAction.LOG):
                    blocked = True
                    self.metrics_collector.record_moderation_action()
                
                # 3. If allowed, evaluate via Co-Host Engine
                if not blocked and ("@goddess" in msg.text.lower() or msg.text.startswith("!")):
                    if msg.text.startswith("!"):
                        self.metrics_collector.record_command()
                    
                    cohost_resp = await cohost_manager.process_message(chat_msg)
                    if cohost_resp:
                        self.metrics_collector.record_cohost_response()

                self.stream_message_history[stream_id].append(msg.message_id)

            except Exception as err:
                self.metrics_collector.record_error()
            finally:
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                self.metrics_collector.record_message_processed(latency_ms=latency_ms, blocked=blocked)

            # Yield control slightly for cooperative async multitasking
            await asyncio.sleep(0)
