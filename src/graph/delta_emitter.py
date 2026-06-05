"""Emit graph change events to all connected WebSocket clients.

The DeltaEmitter is a process-level singleton used by agents to push
live graph updates to the frontend.  Every ``emit()`` call fans out to
all subscribers and silently discards dead connections.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GraphDelta:
    """A single graph change event."""

    type: str
    data: dict[str, Any]
    timestamp: str


class DeltaEmitter:
    """Pub/sub event emitter for WebSocket graph deltas.

    Usage::

        emitter = DeltaEmitter()
        await emitter.subscribe(ws)
        await emitter.emit("node_added", {"id": "...", ...})
    """

    def __init__(self) -> None:
        self._subscribers: list[WebSocket] = []
        self._lock: asyncio.Lock = asyncio.Lock()
        self._event_count: int = 0

    @property
    def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        return len(self._subscribers)

    @property
    def event_count(self) -> int:
        """Return the total number of events emitted."""
        return self._event_count

    async def subscribe(self, ws: WebSocket) -> None:
        """Register a WebSocket connection for delta events."""
        async with self._lock:
            self._subscribers.append(ws)
        logger.info(
            "WebSocket subscriber added",
            extra={"subscriber_count": self.subscriber_count},
        )

    async def unsubscribe(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the subscriber list."""
        async with self._lock:
            try:
                self._subscribers.remove(ws)
            except ValueError:
                pass
        logger.info(
            "WebSocket subscriber removed",
            extra={"subscriber_count": self.subscriber_count},
        )

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Send a delta event to every subscriber.

        Dead connections are collected and removed *after* the emit loop
        to avoid index errors during iteration (see CHALLENGES.md §3).
        """
        delta = GraphDelta(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        message = json.dumps(asdict(delta))
        self._event_count += 1

        dead: list[WebSocket] = []

        async with self._lock:
            for ws in self._subscribers:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)

            for ws in dead:
                try:
                    self._subscribers.remove(ws)
                except ValueError:
                    pass

        if dead:
            logger.info(
                "Removed dead WebSocket connections",
                extra={"removed": len(dead), "remaining": self.subscriber_count},
            )

    async def emit_paper_status(self, paper_id: str, status: str) -> None:
        """Convenience method: emit a paper pipeline status update."""
        await self.emit("paper_status", {"paper_id": paper_id, "status": status})

    async def emit_node_added(self, node_data: dict[str, Any]) -> None:
        """Convenience method: emit a node_added event."""
        await self.emit("node_added", node_data)

    async def emit_edge_added(self, edge_data: dict[str, Any]) -> None:
        """Convenience method: emit an edge_added event."""
        await self.emit("edge_added", edge_data)

    async def emit_edge_updated(self, edge_data: dict[str, Any]) -> None:
        """Convenience method: emit an edge_updated event."""
        await self.emit("edge_updated", edge_data)

    async def emit_question_added(self, question_data: dict[str, Any]) -> None:
        """Convenience method: emit a question_added event."""
        await self.emit("question_added", question_data)

    async def emit_question_resolved(self, question_id: str) -> None:
        """Convenience method: emit a question_resolved event."""
        await self.emit("question_resolved", {"question_id": question_id})
