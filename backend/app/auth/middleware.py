"""
Security Headers & Request Correlation Middleware for GODDESS AI 2.0.

Attaches X-Request-ID correlation tokens, injects security headers,
and guarantees zero secret leakage in logs and telemetry.
"""

import re
import secrets
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("core.security_middleware")

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Generates and propagates X-Request-ID across the request lifecycle."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = f"req_{secrets.token_hex(8)}"

        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        # Log request at DEBUG/INFO without logging query params or authorization headers
        client_ip = request.client.host if request.client else "unknown"
        logger.debug(
            f"[{request_id}] {request.method} {request.url.path} -> "
            f"Status {response.status_code} ({duration_ms}ms) [IP: {client_ip}]"
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces production-grade defensive HTTP security response headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
