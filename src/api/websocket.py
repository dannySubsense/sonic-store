"""WebSocket connection manager: register clients, broadcast messages, handle disconnect."""

from typing import Any, Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """Track active WebSocket connections and broadcast JSON messages to all clients."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        raise NotImplementedError

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active connections list."""
        raise NotImplementedError

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send a JSON message to all connected clients; silently drop failed sends."""
        raise NotImplementedError
