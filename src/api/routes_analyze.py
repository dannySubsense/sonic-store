"""POST /analyze: accept audio file upload, extract features, write to store."""

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/analyze")
async def analyze(file: UploadFile) -> JSONResponse:
    """Load uploaded audio file, extract features from first 2s chunk, return FeatureVector.

    Accepts any format supported by librosa (wav, mp3, flac, ogg).
    Returns 422 if file format is unsupported or audio is too short (<0.5s).
    """
    raise NotImplementedError
