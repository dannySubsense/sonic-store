"""WebSocket connection manager: register clients, broadcast messages, handle disconnect."""

from typing import Any, Dict, List

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class ConnectionManager:
    """Track active WebSocket connections and broadcast JSON messages to all clients."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[ws] Client connected ({len(self.active_connections)} active)")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active connections list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[ws] Client disconnected ({len(self.active_connections)} active)")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send a JSON message to all connected clients. Remove stale connections silently."""
        stale: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for ws in stale:
            if ws in self.active_connections:
                self.active_connections.remove(ws)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a message to a single client."""
        await websocket.send_json(message)
