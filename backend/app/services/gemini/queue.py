"""
Priority-Based Asynchronous Request Queue for Google Gemini API.

Enforces concurrency limits, prioritizes critical requests (e.g. moderation over analytics),
and manages bounded memory queues to prevent overload.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.services.gemini.exceptions import QueueFullError
from app.services.gemini.models import AIRequest, AIResponse, AIResponseStatus

logger = get_logger("gemini.queue")


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    created_at: float
    request: AIRequest = field(compare=False)
    future: asyncio.Future = field(compare=False)


class PriorityRequestQueue:
    """Bounded Priority Queue for scheduling asynchronous Gemini AI requests."""

    def __init__(
        self,
        max_concurrency: Optional[int] = None,
        max_queue_size: Optional[int] = None,
    ):
        self.max_concurrency = max_concurrency or settings.gemini_max_concurrency
        self.max_queue_size = max_queue_size or settings.gemini_queue_max_size
        self._queue: asyncio.PriorityQueue[PrioritizedItem] = asyncio.PriorityQueue(maxsize=self.max_queue_size)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._active_requests = 0
        self._lock = asyncio.Lock()

    @property
    def queued_count(self) -> int:
        return self._queue.qsize()

    @property
    def active_count(self) -> int:
        return self._active_requests

    async def enqueue(self, request: AIRequest) -> asyncio.Future:
        """
        Add a request to the priority queue. Returns a Future that resolves with AIResponse.
        Raises QueueFullError if queue exceeds bounded capacity.
        """
        if self._queue.full():
            logger.warning(f"Gemini request queue full ({self.max_queue_size} items). Dropping request '{request.request_id}'.")
            raise QueueFullError(f"Gemini request queue is full ({self.max_queue_size} items).")

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        item = PrioritizedItem(
            priority=int(request.priority),
            created_at=request.created_at,
            request=request,
            future=future,
        )

        await self._queue.put(item)
        logger.debug(
            f"Enqueued AI request '{request.request_id}' [Stream: {request.stream_id}, Priority: {request.priority.name}]. Queued: {self.queued_count}"
        )
        return future

    async def get_next(self) -> PrioritizedItem:
        """Fetch the next highest priority item from the queue."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark item as processed in priority queue."""
        self._queue.task_done()

    async def acquire_concurrency_slot(self) -> None:
        """Acquire semaphore slot before executing API call."""
        await self._semaphore.acquire()
        async with self._lock:
            self._active_requests += 1

    def release_concurrency_slot(self) -> None:
        """Release semaphore slot after completing or failing API call."""
        self._semaphore.release()
        self._active_requests = max(0, self._active_requests - 1)


# Global singleton instance of PriorityRequestQueue
gemini_queue = PriorityRequestQueue()
