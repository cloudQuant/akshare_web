"""
Lightweight Prometheus-compatible metrics endpoint.

Exposes request counts, latency histograms, and task execution stats
in Prometheus text exposition format without requiring a heavy client library.
"""

import time
import threading
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Response

router = APIRouter()


class _Metrics:
    """Thread-safe in-process metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()
        self._request_count: dict[str, int] = defaultdict(int)  # method:path:status -> count
        self._request_duration_sum: dict[str, float] = defaultdict(float)
        self._task_executions: dict[str, int] = defaultdict(int)  # status -> count
        self._start_time = time.time()

    def record_request(self, method: str, path: str, status: int, duration_s: float) -> None:
        key = f'{method}:{path}:{status}'
        with self._lock:
            self._request_count[key] += 1
            self._request_duration_sum[key] += duration_s

    def record_task_execution(self, status: str) -> None:
        with self._lock:
            self._task_executions[status] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "request_count": dict(self._request_count),
                "request_duration_sum": dict(self._request_duration_sum),
                "task_executions": dict(self._task_executions),
                "uptime_seconds": time.time() - self._start_time,
            }

    def to_prometheus(self) -> str:
        """Render metrics in Prometheus text exposition format."""
        lines: list[str] = []
        snap = self.snapshot()

        lines.append("# HELP akshare_uptime_seconds Time since process start")
        lines.append("# TYPE akshare_uptime_seconds gauge")
        lines.append(f'akshare_uptime_seconds {snap["uptime_seconds"]:.1f}')

        lines.append("# HELP akshare_http_requests_total Total HTTP requests")
        lines.append("# TYPE akshare_http_requests_total counter")
        for key, count in snap["request_count"].items():
            method, path, status = key.rsplit(":", 2)
            # Normalize path to reduce cardinality
            norm_path = _normalize_path(path)
            lines.append(
                f'akshare_http_requests_total{{method="{method}",path="{norm_path}",status="{status}"}} {count}'
            )

        lines.append("# HELP akshare_http_request_duration_seconds_total Sum of HTTP request durations")
        lines.append("# TYPE akshare_http_request_duration_seconds_total counter")
        for key, total in snap["request_duration_sum"].items():
            method, path, status = key.rsplit(":", 2)
            norm_path = _normalize_path(path)
            lines.append(
                f'akshare_http_request_duration_seconds_total{{method="{method}",path="{norm_path}",status="{status}"}} {total:.4f}'
            )

        lines.append("# HELP akshare_task_executions_total Total task executions by status")
        lines.append("# TYPE akshare_task_executions_total counter")
        for status, count in snap["task_executions"].items():
            lines.append(f'akshare_task_executions_total{{status="{status}"}} {count}')

        lines.append("")
        return "\n".join(lines)


def _normalize_path(path: str) -> str:
    """Reduce path cardinality by replacing dynamic segments."""
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append(":id")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized)


# Global singleton
metrics = _Metrics()


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=metrics.to_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
