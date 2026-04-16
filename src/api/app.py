"""FastAPI application: mounts /ui, registers routes, manages lifespan tasks."""

import asyncio
import json
import os
import queue
import time
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
DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "demo"

manager = ConnectionManager()
mic = None  # Lazy-loaded to avoid PortAudio import failure on headless machines
mic_running = False
mic_task = None
generation_engine = None


def _get_mic():
    """Lazy-load MicIngestion to avoid import failure when PortAudio is missing."""
    global mic
    if mic is None:
        from src.ingestion.mic import MicIngestion
        mic = MicIngestion()
    return mic


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: select store, start generation engine. Shutdown: stop everything."""
    global generation_engine

    app.state.store = get_store()

    # Start GenerationEngine in background thread (model loads lazily)
    from src.generation.engine import GenerationEngine
    generation_engine = GenerationEngine(
        store=app.state.store,
    )
    generation_engine.start()
    app.state.generation_engine = generation_engine

    # Async task to poll generation output queue and broadcast to WebSocket clients
    broadcast_task = asyncio.create_task(_generation_broadcast_loop())

    yield

    # Cleanup
    global mic_running
    if mic_running:
        mic_running = False
        if mic is not None:
            mic.stop()

    if generation_engine is not None:
        generation_engine.stop()
        generation_engine = None

    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass


async def _generation_broadcast_loop() -> None:
    """Poll GenerationEngine output_queue and broadcast GenerationMessages."""
    while True:
        try:
            if generation_engine is None:
                await asyncio.sleep(1.0)
                continue
            try:
                clip = generation_engine.output_queue.get_nowait()
                await manager.broadcast({
                    "type": "generation",
                    "data": {
                        "audio_b64": clip.audio_b64,
                        "prompt": clip.prompt,
                        "duration_seconds": clip.duration_seconds,
                        "generation_time_ms": clip.generation_time_ms,
                        "features_snapshot": clip.features_snapshot,
                    }
                })
            except queue.Empty:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[broadcast] Error: {e}")
            await asyncio.sleep(1.0)


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
            await manager.broadcast({
                "type": "error",
                "code": "extraction_failed",
                "message": str(e),
            })
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
                            "message": "Grant microphone permission in System Settings",
                        })

                elif action == "stop_mic" and mic_running:
                    mic_running = False
                    _get_mic().stop()
                    if mic_task:
                        mic_task.cancel()
                        mic_task = None
                    print("[ws] Mic loop stopped")

                elif action == "trigger_generation":
                    print("[ws] Manual generation trigger received")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


def get_app_store_from_app():
    """Get store from app state for use outside request context."""
    if not hasattr(app.state, "store"):
        from src.store.dict_store import DictStore
        app.state.store = DictStore()
    return app.state.store


# --- S11: Status endpoint ---

@app.get("/status")
async def get_status() -> dict:
    """Return system status: store type, model state, mic state, connections."""
    store = get_app_store_from_app()
    store_type = type(store).__name__.lower()
    if "redis" in store_type:
        store_type = "redis"
    else:
        store_type = "dict"

    model_loaded = False
    if generation_engine is not None:
        model_loaded = generation_engine.model_loaded

    history = store.get_history(limit=30)
    features_count = len(history)

    return {
        "store": store_type,
        "model_loaded": model_loaded,
        "mic_running": mic_running,
        "connections": len(manager.active_connections),
        "features_count": features_count,
    }


# --- S11: Demo mode endpoint ---

@app.post("/demo/start")
async def demo_start() -> dict:
    """Load WAV files from demo/ directory, analyze each, broadcast features."""
    if not DEMO_DIR.is_dir():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="demo/ directory not found")

    wav_files = sorted(DEMO_DIR.glob("*.wav"))
    if not wav_files:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No WAV files in demo/ directory")

    store = get_app_store_from_app()
    results = []

    for wav_path in wav_files:
        try:
            from src.ingestion.file import load_and_chunk
            chunks = load_and_chunk(str(wav_path))
            first_chunk = next(chunks)
            features = extract_features(first_chunk, source="file")
            store.write(features)
            await manager.broadcast({"type": "features", "data": features})
            results.append({"file": wav_path.name, "status": "ok"})
            await asyncio.sleep(0.5)
        except Exception as e:
            results.append({"file": wav_path.name, "status": "error", "detail": str(e)})

    return {"files_processed": len(results), "results": results}


# Debug-only broadcast endpoint for testing
if os.getenv("DEBUG_MODE", "").lower() == "true":
    @app.post("/test/broadcast")
    async def test_broadcast(request: Request) -> dict:
        """Broadcast a message to all WebSocket clients. DEBUG_MODE only."""
        body = await request.json()
        message = body.get("message", body)
        await manager.broadcast(message)
        return {"status": "broadcast_sent", "clients": len(manager.active_connections)}
