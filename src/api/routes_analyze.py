"""POST /analyze: accept audio file upload, extract features, write to store."""

import tempfile

from fastapi import APIRouter, HTTPException, Request, UploadFile

from src.features.engine import extract_features
from src.ingestion.file import load_and_chunk

router = APIRouter()


@router.post("/analyze")
async def analyze(file: UploadFile, request: Request) -> dict:
    """Load uploaded audio, extract features from first 2s chunk, return FeatureVector."""
    from src.api.app import get_app_store
    store = get_app_store(request)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()

        try:
            chunks = load_and_chunk(tmp.name)
            first_chunk = next(chunks)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception:
            raise HTTPException(status_code=422, detail="Unsupported audio format")

    features = extract_features(first_chunk, source="file")
    store.write(features)
    return features
