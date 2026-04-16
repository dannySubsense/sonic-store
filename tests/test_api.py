"""API tests for POST /analyze, GET /features/latest, GET /features/history."""

import io
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.store.dict_store import DictStore

SAMPLE_RATE = 22050


@pytest.fixture(autouse=True)
def reset_store() -> None:
    """Reset the app store before each test to prevent cross-test contamination."""
    app.state.store = DictStore()


def make_wav_bytes(freq: float = 440.0, duration_s: float = 2.0) -> bytes:
    """Generate a WAV file in memory and return its bytes."""
    samples = int(SAMPLE_RATE * duration_s)
    t = np.arange(samples, dtype=np.float32) / SAMPLE_RATE
    audio = np.sin(2 * np.pi * freq * t).astype(np.float32)
    buf = io.BytesIO()
    wavfile.write(buf, SAMPLE_RATE, audio)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def wav_440() -> bytes:
    return make_wav_bytes(440.0, 2.0)


@pytest.fixture
def short_wav() -> bytes:
    """WAV shorter than 0.5s — should be rejected."""
    return make_wav_bytes(440.0, 0.1)


@pytest.mark.asyncio
async def test_post_analyze_returns_feature_vector(wav_440: bytes) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/analyze", files={"file": ("test.wav", wav_440, "audio/wav")})
    assert resp.status_code == 200
    data = resp.json()
    required_keys = {
        "timestamp", "chunk_index", "source", "duration_seconds",
        "chroma", "bpm", "key_pitch_class", "key_mode",
        "rms_energy", "spectral_centroid_hz", "onset_strength",
        "mel_spectrogram", "waveform_display",
    }
    assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"


@pytest.mark.asyncio
async def test_post_analyze_empty_file_returns_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/analyze", files={"file": ("empty.wav", b"", "audio/wav")})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_analyze_text_file_returns_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/analyze",
            files={"file": ("notes.txt", b"not audio data", "text/plain")},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_latest_before_any_post_returns_404() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/features/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_then_get_latest_returns_features(wav_440: bytes) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post_resp = await client.post("/analyze", files={"file": ("test.wav", wav_440, "audio/wav")})
        assert post_resp.status_code == 200

        get_resp = await client.get("/features/latest")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "chroma" in data
        assert len(data["chroma"]) == 12


@pytest.mark.asyncio
async def test_post_twice_then_history_returns_two(wav_440: bytes) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/analyze", files={"file": ("a.wav", wav_440, "audio/wav")})
        await client.post("/analyze", files={"file": ("b.wav", wav_440, "audio/wav")})

        resp = await client.get("/features/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 2


@pytest.mark.asyncio
async def test_history_limit_param(wav_440: bytes) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/analyze", files={"file": ("a.wav", wav_440, "audio/wav")})
        await client.post("/analyze", files={"file": ("b.wav", wav_440, "audio/wav")})
        await client.post("/analyze", files={"file": ("c.wav", wav_440, "audio/wav")})

        resp = await client.get("/features/history?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_history_limit_clamped_to_30(wav_440: bytes) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/features/history?limit=999")
    # FastAPI Query(le=30) returns 422 for limit > 30
    assert resp.status_code == 422
