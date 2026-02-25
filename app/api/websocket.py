"""
WebSocket endpoint for real-time task execution status updates.

Clients connect to /ws/executions and receive JSON messages whenever
a task execution changes status (PENDING → RUNNING → COMPLETED/FAILED).
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from loguru import logger

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager (pub/sub hub)
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.debug(f"WebSocket connected, total={len(self._connections)}")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c is not ws]
        logger.debug(f"WebSocket disconnected, total={len(self._connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to all connected clients."""
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        stale: list[WebSocket] = []

        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)

            # Clean up broken connections
            for ws in stale:
                self._connections = [c for c in self._connections if c is not ws]

    @property
    def active_count(self) -> int:
        return len(self._connections)


# Global singleton
ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper to broadcast from anywhere in the codebase
# ---------------------------------------------------------------------------

async def broadcast_execution_update(
    execution_id: str,
    task_id: int | None,
    status: str,
    *,
    rows_before: int | None = None,
    rows_after: int | None = None,
    error_message: str | None = None,
    duration: float | None = None,
) -> None:
    """Broadcast an execution status change to all WebSocket clients.

    Call this from scheduler / execution_service whenever status changes.
    """
    await ws_manager.broadcast({
        "type": "execution_update",
        "data": {
            "execution_id": execution_id,
            "task_id": task_id,
            "status": status,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "error_message": error_message,
            "duration": duration,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/executions")
async def execution_updates(ws: WebSocket):
    """
    WebSocket endpoint for real-time execution updates.

    Clients simply connect and receive JSON messages:
    ```json
    {
      "type": "execution_update",
      "data": {
        "execution_id": "exec_20250225_...",
        "task_id": 42,
        "status": "running",
        "timestamp": "2025-02-25T12:00:00+00:00"
      }
    }
    ```
    """
    await ws_manager.connect(ws)
    try:
        # Keep connection alive; handle any client messages (ping/pong)
        while True:
            data = await ws.receive_text()
            # Clients can send "ping" to keep alive
            if data.strip().lower() == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(ws)
