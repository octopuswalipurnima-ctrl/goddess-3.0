"""
Asynchronous Internal Event Bus for GODDESS AI 2.0.

Decouples internal subsystems (Streams, Moderation, AI, Commands, XP, VIP, WebSockets)
by allowing components to publish events and subscribe to them independently.
"""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List
from app.core.logging import get_logger

logger = get_logger("event_bus")

# Event Handler Type: Async function receiving payload dict/object
EventHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Internal lightweight Pub/Sub Event Bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register an async handler for a given event name."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        if handler not in self._subscribers[event_name]:
            self._subscribers[event_name].append(handler)
            logger.debug(f"Subscribed handler '{handler.__name__}' to event '{event_name}'")

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove an async handler for a given event name."""
        if event_name in self._subscribers and handler in self._subscribers[event_name]:
            self._subscribers[event_name].remove(handler)
            logger.debug(f"Unsubscribed handler '{handler.__name__}' from event '{event_name}'")

    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event asynchronously to all registered subscribers.
        Each handler executes in isolated try/except so one failure cannot crash others.
        """
        handlers = self._subscribers.get(event_name, [])
        if not handlers:
            logger.debug(f"No subscribers registered for event '{event_name}'")
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._safe_execute_handler(handler, event_name, payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute_handler(
        self, handler: EventHandler, event_name: str, payload: Dict[str, Any]
    ) -> None:
        try:
            await handler(payload)
        except Exception as e:
            logger.error(
                f"Error in event handler '{handler.__name__}' for event '{event_name}': {str(e)}",
                exc_info=True,
            )


# Global singleton instance of EventBus
event_bus = EventBus()
