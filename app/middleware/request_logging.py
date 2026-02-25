"""
Request logging middleware.

Logs request ID, method, path, status code, and response time for every request.
"""

import time
import uuid

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request details and response time."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        # Skip logging for health checks and static files
        path = request.url.path
        skip_log = path in ("/health",) or path.startswith("/assets/")

        if not skip_log:
            logger.info(
                f"[{request_id}] {request.method} {path}"
            )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {path} "
                f"500 ({duration_ms:.1f}ms)"
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        if not skip_log:
            log_fn = logger.info if response.status_code < 400 else logger.warning
            log_fn(
                f"[{request_id}] {request.method} {path} "
                f"{response.status_code} ({duration_ms:.1f}ms)"
            )

        response.headers["X-Request-ID"] = request_id
        return response
