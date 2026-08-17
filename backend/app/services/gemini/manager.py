"""
Centralized Gemini AI Manager for GODDESS AI 2.0.

Orchestrates priority queueing, token bucket rate limiting, credential rotation,
model routing with fallbacks, response normalization, metrics, and multi-stream isolation.
"""

import asyncio
import time
from typing import Optional

from app.core.config import settings
from app.core.events import event_bus
from app.core.logging import get_logger
from app.services.gemini.client import GeminiAPIClient, gemini_client
from app.services.gemini.credentials import GeminiCredentialManager, gemini_credentials
from app.services.gemini.exceptions import (
    AuthenticationError,
    CredentialUnavailableError,
    EmptyResponseError,
    GeminiAPIError,
    InvalidRequestError,
    ModelUnavailableError,
    QuotaExceededError,
    RateLimitError,
    RequestTimeoutError,
)
from app.services.gemini.models import (
    AIRequest,
    AIResponse,
    AIResponseStatus,
    GeminiMetrics,
)
from app.services.gemini.queue import PriorityRequestQueue, gemini_queue
from app.services.gemini.rate_limiter import TokenBucketRateLimiter, gemini_rate_limiter
from app.services.gemini.router import ModelRouter, gemini_router

logger = get_logger("gemini.manager")


class GeminiAIManager:
    """Central orchestrator for all Google Gemini AI operations."""

    def __init__(
        self,
        credentials: Optional[GeminiCredentialManager] = None,
        client: Optional[GeminiAPIClient] = None,
        router: Optional[ModelRouter] = None,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        queue: Optional[PriorityRequestQueue] = None,
        max_retries: Optional[int] = None,
    ):
        self.credentials = credentials or gemini_credentials
        self.client = client or gemini_client
        self.router = router or gemini_router
        self.rate_limiter = rate_limiter or gemini_rate_limiter
        self.queue = queue or gemini_queue
        self.max_retries = max_retries if max_retries is not None else settings.gemini_max_retries
        self.metrics = GeminiMetrics()

        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background queue processor worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._queue_worker(), name="gemini-queue-worker")
        logger.info("Gemini AI Manager background queue worker started.")

    async def shutdown(self) -> None:
        """Gracefully stop queue worker and cancel pending requests."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Gemini AI Manager shutdown complete.")

    async def request(self, request: AIRequest) -> AIResponse:
        """
        Public entrypoint for submitting an AI generation request.
        Enqueues the request according to priority and awaits the normalized AIResponse.
        """
        self.metrics.total_requests += 1

        # Publish creation event
        await event_bus.publish(
            "AI_REQUEST_CREATED",
            {
                "request_id": request.request_id,
                "stream_id": request.stream_id,
                "source": request.source,
                "priority": request.priority.name,
            },
        )

        # If queue worker isn't running, start it
        if not self._running:
            await self.start()

        # Enqueue and await response future
        future = await self.queue.enqueue(request)
        return await future

    async def _queue_worker(self) -> None:
        """Continuous background worker pulling from priority queue and executing requests."""
        while self._running:
            try:
                item = await self.queue.get_next()
            except asyncio.CancelledError:
                break

            # Process request asynchronously in an isolated concurrency task
            asyncio.create_task(self._process_item(item))
            self.queue.task_done()

    async def _process_item(self, item) -> None:
        """Process a single queued item with semaphore concurrency control and rate limiting."""
        request = item.request
        future = item.future

        await self.queue.acquire_concurrency_slot()
        self.metrics.active_requests = self.queue.active_count
        self.metrics.queued_requests = self.queue.queued_count

        start_time = time.time()
        try:
            await event_bus.publish(
                "AI_REQUEST_STARTED",
                {"request_id": request.request_id, "stream_id": request.stream_id},
            )

            # 1. Acquire Token Bucket Rate Limit
            await self.rate_limiter.acquire(tokens=1.0, timeout=request.timeout_seconds)

            # 2. Execute with Retry, Credential Rotation, and Model Fallback
            response = await self._execute_request_pipeline(request, start_time)

            # 3. Update Metrics & Event Dispatches
            latency = response.latency_seconds
            if response.status == AIResponseStatus.SUCCESS:
                self.metrics.successful_requests += 1
                self.metrics.total_latency_seconds += latency
                await event_bus.publish(
                    "AI_REQUEST_COMPLETED",
                    {
                        "request_id": request.request_id,
                        "stream_id": request.stream_id,
                        "model": response.model,
                        "latency": latency,
                    },
                )
            else:
                self.metrics.failed_requests += 1
                await event_bus.publish(
                    "AI_REQUEST_FAILED",
                    {
                        "request_id": request.request_id,
                        "stream_id": request.stream_id,
                        "status": response.status.value,
                        "error": response.error_message,
                    },
                )

            if not future.done():
                future.set_result(response)

        except Exception as exc:
            logger.error(f"Unexpected error processing AI request '{request.request_id}': {exc}", exc_info=True)
            self.metrics.failed_requests += 1
            err_resp = AIResponse(
                request_id=request.request_id,
                stream_id=request.stream_id,
                status=AIResponseStatus.UNKNOWN_ERROR,
                text="",
                model="",
                error_message=str(exc),
                latency_seconds=round(time.time() - start_time, 3),
            )
            if not future.done():
                future.set_result(err_resp)

        finally:
            self.queue.release_concurrency_slot()
            self.metrics.active_requests = self.queue.active_count
            self.metrics.queued_requests = self.queue.queued_count

    async def _execute_request_pipeline(self, request: AIRequest, start_time: float) -> AIResponse:
        """
        Executes the API request with automatic retries, credential rotation, and model fallback.
        """
        attempts = 0
        use_fallback_model = False
        last_error_status = AIResponseStatus.UNKNOWN_ERROR
        last_error_msg = ""
        current_credential_id = None
        current_model = self.router.select_model(request, use_fallback=False)

        while attempts <= self.max_retries:
            attempts += 1
            current_model = self.router.select_model(request, use_fallback=use_fallback_model)

            try:
                key_id, raw_key = self.credentials.get_credential()
                current_credential_id = key_id
            except CredentialUnavailableError as e:
                logger.error(f"No Gemini credentials available for request '{request.request_id}': {e}")
                return AIResponse(
                    request_id=request.request_id,
                    stream_id=request.stream_id,
                    status=AIResponseStatus.AUTH_ERROR,
                    text="",
                    model=current_model,
                    error_message=str(e),
                    latency_seconds=round(time.time() - start_time, 3),
                )

            try:
                text, finish_reason, token_usage = await self.client.generate_content(
                    prompt=request.prompt,
                    model=current_model,
                    raw_key=raw_key,
                    system_instruction=request.system_instruction,
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                    timeout=request.timeout_seconds,
                )

                # Successful generation
                await self.credentials.mark_success(key_id)
                latency = round(time.time() - start_time, 3)

                return AIResponse(
                    request_id=request.request_id,
                    stream_id=request.stream_id,
                    status=AIResponseStatus.SUCCESS,
                    text=text,
                    model=current_model,
                    credential_id=key_id,
                    finish_reason=finish_reason,
                    latency_seconds=latency,
                    token_usage=token_usage,
                    metadata=request.metadata,
                )

            except EmptyResponseError as exc:
                self.metrics.empty_responses += 1
                logger.warning(f"Gemini empty response on '{request.request_id}' with model '{current_model}': {exc}")
                last_error_status = AIResponseStatus.EMPTY_RESPONSE
                last_error_msg = str(exc)

                # Attempt model fallback on empty response if primary was used
                if not use_fallback_model and not request.model_preference:
                    use_fallback_model = True
                    self.metrics.model_fallbacks_count += 1
                    await self.router.notify_fallback(request.request_id, request.stream_id, str(exc))
                    continue
                break

            except (QuotaExceededError, RateLimitError) as exc:
                self.metrics.rate_limited_count += 1
                self.metrics.retries_count += 1
                is_quota = isinstance(exc, QuotaExceededError)
                last_error_status = AIResponseStatus.RATE_LIMITED
                last_error_msg = str(exc)

                await self.credentials.mark_failed(key_id, str(exc), is_quota=is_quota)
                logger.warning(f"Gemini credential '{key_id}' rate limited / quota exceeded. Rotating...")

                # Apply exponential backoff delay before retry
                await asyncio.sleep(min(2.0 ** attempts, 5.0))
                continue

            except ModelUnavailableError as exc:
                self.metrics.model_fallbacks_count += 1
                last_error_status = AIResponseStatus.MODEL_ERROR
                last_error_msg = str(exc)

                if not use_fallback_model and not request.model_preference:
                    use_fallback_model = True
                    await self.router.notify_fallback(request.request_id, request.stream_id, str(exc))
                    continue
                break

            except RequestTimeoutError as exc:
                self.metrics.timeouts += 1
                last_error_status = AIResponseStatus.TIMEOUT
                last_error_msg = str(exc)
                logger.warning(f"Request '{request.request_id}' timed out on attempt {attempts}.")
                break

            except (InvalidRequestError, AuthenticationError) as exc:
                last_error_status = (
                    AIResponseStatus.INVALID_REQUEST
                    if isinstance(exc, InvalidRequestError)
                    else AIResponseStatus.AUTH_ERROR
                )
                last_error_msg = str(exc)
                logger.error(f"Non-retryable Gemini error for '{request.request_id}': {exc}")
                break

            except GeminiAPIError as exc:
                self.metrics.retries_count += 1
                last_error_status = AIResponseStatus.PROVIDER_ERROR
                last_error_msg = str(exc)

                # Check if error suggests model fallback
                if self.router.should_fallback(exc) and not use_fallback_model and not request.model_preference:
                    use_fallback_model = True
                    self.metrics.model_fallbacks_count += 1
                    await self.router.notify_fallback(request.request_id, request.stream_id, str(exc))

                await asyncio.sleep(min(1.5 ** attempts, 4.0))
                continue

        # Exhausted retries or non-retryable error
        latency = round(time.time() - start_time, 3)
        return AIResponse(
            request_id=request.request_id,
            stream_id=request.stream_id,
            status=last_error_status,
            text="",
            model=current_model,
            credential_id=current_credential_id,
            error_message=last_error_msg or "Max retries exceeded without successful response.",
            latency_seconds=latency,
            metadata=request.metadata,
        )


# Global singleton instance of GeminiAIManager
gemini_manager = GeminiAIManager()
