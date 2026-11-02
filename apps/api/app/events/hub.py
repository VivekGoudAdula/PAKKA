"""
WebSocket event hub.

Manages connections and broadcasts real-time events to connected frontend clients.
Event types are defined in ARCHITECTURE.md.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


class EventHub:
    """Tracks active WebSocket connections and broadcasts events to all of them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the registry."""
        self._connections.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        """
        Send a JSON event to all connected clients.

        Args:
            event_type: One of the event type strings defined in ARCHITECTURE.md.
            payload: Optional dictionary of event data.
        """
        message = json.dumps({"type": event_type, "payload": payload or {}})
        dead: set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                # Connection died — mark for cleanup
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)


# Singleton hub — shared across the process
hub = EventHub()


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time event streaming.

    The client receives JSON events as they occur (call.started, transcript, etc.).
    The client may also send control messages (e.g. demo.clock.set_speed).
    """
    await hub.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON WS message: %s", raw[:200])
                continue

            msg_type = msg.get("type", "")
            logger.debug("WS message received: %s", msg_type)

            # Route inbound control messages
            if msg_type == "demo.clock.set_speed":
                # Handled by the demo clock service in Phase 7
                pass
            elif msg_type == "demo.trigger_call":
                # Handled by the demo call simulator in Phase 10
                pass
            elif msg_type == "subscribe":
                # Topic subscriptions — Phase 3+
                pass
            else:
                logger.warning("Unknown WS message type: %s", msg_type)

    except WebSocketDisconnect:
        hub.disconnect(ws)

