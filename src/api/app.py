"""FastAPI application: mounts /ui, registers routes, manages lifespan tasks."""

import asyncio
import json
import os
import queue
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from src.api.routes_analyze import router as analyze_router
from src.api.routes_features import router as features_router
from src.api.websocket import ConnectionManager
from src.features.engine import extract_features
from src.store import get_store

UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui"

manager = ConnectionManager()
mic = None  # Lazy-loaded to avoid PortAudio import failure on headless machines
mic_running = False
mic_task = None


def _get_mic():
    """Lazy-load MicIngestion to avoid import failure when PortAudio is missing."""
    global mic
    if mic is None:
        from src.ingestion.mic import MicIngestion
        mic = MicIngestion()
    return mic


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: select store backend, instantiate mic. Shutdown: stop mic."""
    app.state.store = get_store()
    yield
    # Cleanup
    global mic_running
    if mic_running:
        mic_running = False
        if mic is not None:
            mic.stop()


app = FastAPI(title="SonicStore", version="1.0.0", lifespan=lifespan)

app.include_router(analyze_router)
app.include_router(features_router)

if UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


def get_app_store(request: Request):
    """Get the store from app state, initializing if needed (test support)."""
    if not hasattr(request.app.state, "store"):
        from src.store.dict_store import DictStore
        request.app.state.store = DictStore()
    return request.app.state.store


async def mic_loop(store) -> None:
    """Async loop: poll mic queue, extract features, store, broadcast."""
    global mic_running
    loop = asyncio.get_event_loop()

    while mic_running:
        try:
            chunk = await loop.run_in_executor(
                None, lambda: _get_mic().output_queue.get(timeout=1.0)
            )
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[mic_loop] Error getting chunk: {e}")
            continue

        try:
            features = await loop.run_in_executor(
                None, lambda: extract_features(chunk, source="mic")
            )
        except Exception as e:
            print(f"[mic_loop] Feature extraction error: {e}")
            await manager.broadcast({
                "type": "error",
                "code": "extraction_failed",
                "message": str(e),
            })
            continue

        try:
            store.write(features)
        except Exception as e:
            print(f"[mic_loop] Store write error: {e}")

        await manager.broadcast({"type": "features", "data": features})


@app.websocket("/ws/features")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint: stream FeatureMessages and GenerationMessages to clients."""
    global mic_running, mic_task

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

                if action == "start_mic" and not mic_running:
                    try:
                        _get_mic().start()
                        mic_running = True
                        store = get_app_store_from_app()
                        mic_task = asyncio.create_task(mic_loop(store))
                        print("[ws] Mic loop started")
                    except Exception as e:
                        print(f"[ws] Failed to start mic: {e}")
                        await manager.broadcast({
                            "type": "error",
                            "code": "mic_unavailable",
                            "message": str(e),
                        })

                elif action == "stop_mic" and mic_running:
                    mic_running = False
                    _get_mic().stop()
                    if mic_task:
                        mic_task.cancel()
                        mic_task = None
                    print("[ws] Mic loop stopped")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


def get_app_store_from_app():
    """Get store from app state for use outside request context."""
    if not hasattr(app.state, "store"):
        from src.store.dict_store import DictStore
        app.state.store = DictStore()
    return app.state.store


# Debug-only broadcast endpoint for testing
if os.getenv("DEBUG_MODE", "").lower() == "true":
    @app.post("/test/broadcast")
    async def test_broadcast(request: Request) -> dict:
        """Broadcast a message to all WebSocket clients. DEBUG_MODE only."""
        body = await request.json()
        message = body.get("message", body)
        await manager.broadcast(message)
        return {"status": "broadcast_sent", "clients": len(manager.active_connections)}
