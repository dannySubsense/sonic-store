"""GET /features/* endpoints: latest, history, and stream-trigger."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/features/latest")
async def get_latest() -> JSONResponse:
    """Return the most recently extracted FeatureVector, or 404 if none yet."""
    raise NotImplementedError


@router.get("/features/history")
async def get_history(limit: int = Query(default=30, ge=1, le=30)) -> JSONResponse:
    """Return up to limit FeatureVector entries, newest first. Empty array if no history."""
    raise NotImplementedError


@router.get("/features/stream-trigger")
async def set_stream_trigger(
    interval: float = Query(default=1.0, ge=0.1)
) -> JSONResponse:
    """Set the generation trigger interval on the GenerationEngine."""
    raise NotImplementedError
