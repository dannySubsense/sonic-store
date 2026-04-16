"""FastAPI application: mounts /ui, registers routes, manages lifespan tasks."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket

from src.api.routes_analyze import router as analyze_router
from src.api.routes_features import router as features_router
from src.store import get_store


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
    # S06: will be implemented with ConnectionManager
    raise NotImplementedError
