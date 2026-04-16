"""FastAPI application: mounts /ui, registers routes, manages lifespan tasks."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket

from src.api.routes_analyze import router as analyze_router
from src.api.routes_features import router as features_router
from src.api.websocket import ConnectionManager


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: select store backend, init generation engine, start mic loop.

    Shutdown: stop generation engine and mic stream.
    """
    # TODO: select store backend (RedisStore or DictStore fallback)
    # TODO: init GenerationEngine and start background thread
    # TODO: optionally start MicIngestion background task
    yield
    # TODO: stop GenerationEngine thread
    # TODO: stop MicIngestion stream


app = FastAPI(title="SonicStore", version="1.0.0", lifespan=lifespan)

app.include_router(analyze_router)
app.include_router(features_router)


@app.websocket("/ws/features")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint: stream FeatureMessages and GenerationMessages to clients."""
    raise NotImplementedError


# Mount UI static files at /ui
# app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
