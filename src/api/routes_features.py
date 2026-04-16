"""GET /features/* endpoints: latest and history."""

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/features/latest")
async def get_latest(request: Request) -> dict:
    """Return the most recently extracted FeatureVector, or 404 if none yet."""
    from src.api.app import get_app_store
    store = get_app_store(request)

    result = store.get_latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No features extracted yet")
    return result


@router.get("/features/history")
async def get_history(
    request: Request,
    limit: int = Query(default=30, ge=1, le=30),
) -> list:
    """Return up to limit FeatureVector entries, newest first."""
    from src.api.app import get_app_store
    store = get_app_store(request)

    return store.get_history(limit=limit)
