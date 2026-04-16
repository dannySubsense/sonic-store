"""FastAPI application: mounts /ui, registers routes, manages lifespan tasks."""

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from src.api.routes_analyze import router as analyze_router
from src.api.routes_features import router as features_router
from src.api.websocket import ConnectionManager
from src.store import get_store


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: select store backend. Shutdown: cleanup."""
    app.state.store = get_store()
    yield


app = FastAPI(title="SonicStore", version="1.0.0", lifespan=lifespan)

app.include_router(analyze_router)
app.include_router(features_router)


def get_app_store(request: Request):
    """Get the store from app state, initializing if needed (test support)."""
    if not hasattr(request.app.state, "store"):
        from src.store.dict_store import DictStore
        request.app.state.store = DictStore()
    return request.app.state.store


@app.websocket("/ws/features")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint: stream FeatureMessages and GenerationMessages to clients."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "control":
                action = msg.get("action", "")
                print(f"[ws] Control message received: {action}")
                # S09: start_mic/stop_mic will be wired here
                # S10: trigger_generation will be wired here
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


# Debug-only broadcast endpoint for testing
if os.getenv("DEBUG_MODE", "").lower() == "true":
    @app.post("/test/broadcast")
    async def test_broadcast(request: Request) -> dict:
        """Broadcast a message to all WebSocket clients. DEBUG_MODE only."""
        body = await request.json()
        message = body.get("message", body)
        await manager.broadcast(message)
        return {"status": "broadcast_sent", "clients": len(manager.active_connections)}
