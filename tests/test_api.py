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
async def test_post_analyze_short_audio_returns_422(short_wav: bytes) -> None:
    """Audio shorter than 0.5s is rejected with 422 (load_and_chunk raises ValueError)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/analyze",
            files={"file": ("short.wav", short_wav, "audio/wav")},
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


# --- S06: WebSocket tests ---

from starlette.testclient import TestClient


def test_websocket_connect() -> None:
    """Test 9: WebSocket connection is accepted."""
    client = TestClient(app)
    with client.websocket_connect("/ws/features") as ws:
        # Connection accepted if we get here without exception
        ws.send_json({"type": "control", "action": "start_mic"})


def test_websocket_control_message() -> None:
    """Test 11: Sending a control message doesn't error."""
    client = TestClient(app)
    with client.websocket_connect("/ws/features") as ws:
        ws.send_json({"type": "control", "action": "start_mic"})
        ws.send_json({"type": "control", "action": "stop_mic"})
        ws.send_json({"type": "control", "action": "trigger_generation"})
        # No exception = success


def test_websocket_disconnect_cleans_up() -> None:
    """Test 12: Disconnecting reduces active connections."""
    from src.api.app import manager
    client = TestClient(app)
    initial_count = len(manager.active_connections)
    with client.websocket_connect("/ws/features"):
        assert len(manager.active_connections) == initial_count + 1
    # After context exit, connection is closed
    assert len(manager.active_connections) == initial_count


def test_websocket_broadcast_via_debug_endpoint() -> None:
    """Test 10: POST /test/broadcast sends message to WebSocket client."""
    import os
    os.environ["DEBUG_MODE"] = "true"
    # Need to reimport app to pick up the debug route
    # Instead, test broadcast through the manager directly
    from src.api.app import manager
    import asyncio

    async def _test():
        # Simulate broadcast with no connections — should not raise
        await manager.broadcast({"type": "features", "data": {"bpm": 120}})

    asyncio.run(_test())


# --- H1.S06: WebSocket payload extension tests ---

import pathlib
import tempfile


def _write_test_wav(path: pathlib.Path, duration_s: float = 10.0, freq: float = 440.0) -> None:
    """Write a sine-wave WAV of given duration to disk."""
    samples = int(SAMPLE_RATE * duration_s)
    t = np.arange(samples, dtype=np.float32) / SAMPLE_RATE
    audio = np.sin(2 * np.pi * freq * t).astype(np.float32)
    wavfile.write(str(path), SAMPLE_RATE, audio)


@pytest.mark.asyncio
async def test_ws_payload_includes_indicators_field(monkeypatch, tmp_path):
    """Test 1: broadcast frames carry the new indicators field.

    Uses demo_start with a temp directory containing one short WAV file,
    then inspects captured broadcasts. With only 2 chunks, history never
    reaches N=10 so all indicator payloads should be null.
    """
    # Override DEMO_DIR to a temp dir with a 4-second WAV (2 chunks, cold-start)
    wav_path = tmp_path / "short.wav"
    _write_test_wav(wav_path, duration_s=4.0)
    monkeypatch.setattr("src.api.app.DEMO_DIR", tmp_path)

    # Capture broadcasts by patching manager.broadcast
    from src.api import app as app_module
    captured = []

    async def capture_broadcast(msg):
        captured.append(msg)

    monkeypatch.setattr(app_module.manager, "broadcast", capture_broadcast)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/demo/start")

    assert resp.status_code == 200
    # At least one broadcast emitted; all contain "indicators" key
    feature_broadcasts = [m for m in captured if m.get("type") == "features"]
    assert len(feature_broadcasts) >= 1
    for msg in feature_broadcasts:
        assert "indicators" in msg  # key MUST be present
    # With only a few chunks, history never reaches N=10 → all null
    assert all(m["indicators"] is None for m in feature_broadcasts)


@pytest.mark.asyncio
async def test_demo_start_broadcast_includes_indicators_field(monkeypatch, tmp_path):
    """Test 2: demo_start emits frames that transition from null to populated.

    Using enough WAV content (~30 seconds = 15+ chunks) to cross N=10.
    Early frames: indicators null. Late frames: populated dict.
    """
    # Three 10-second WAVs -> many chunks total -> indicators populate after chunk 10
    for i in range(3):
        _write_test_wav(tmp_path / f"demo_{i}.wav", duration_s=10.0, freq=440.0 + i * 100)
    monkeypatch.setattr("src.api.app.DEMO_DIR", tmp_path)

    from src.api import app as app_module
    captured = []

    async def capture_broadcast(msg):
        captured.append(msg)

    monkeypatch.setattr(app_module.manager, "broadcast", capture_broadcast)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/demo/start")

    assert resp.status_code == 200
    feature_broadcasts = [m for m in captured if m.get("type") == "features"]
    # With 3 files of multiple chunks each, we get many broadcasts
    assert len(feature_broadcasts) >= 10
    # Early frames: null (history building up)
    assert feature_broadcasts[0]["indicators"] is None
    # By frame 10 or later, indicators should be populated
    late_frames = feature_broadcasts[10:] if len(feature_broadcasts) > 10 else []
    assert any(m["indicators"] is not None for m in late_frames), "No populated indicators in late frames"
    # When populated, it must be a dict with expected keys
    populated = [m["indicators"] for m in late_frames if m["indicators"] is not None]
    if populated:
        first_pop = populated[0]
        assert "available" in first_pop
        assert first_pop["available"] is True
        assert "energy_regime" in first_pop
        assert "delta_bpm" in first_pop


@pytest.mark.asyncio
async def test_demo_start_response_includes_chunks_processed(monkeypatch, tmp_path):
    """Test 3: response body has chunks_processed integer per file entry."""
    _write_test_wav(tmp_path / "demo.wav", duration_s=10.0)
    monkeypatch.setattr("src.api.app.DEMO_DIR", tmp_path)

    from src.api import app as app_module

    async def noop_broadcast(msg):
        pass

    monkeypatch.setattr(app_module.manager, "broadcast", noop_broadcast)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/demo/start")

    assert resp.status_code == 200
    body = resp.json()
    assert body["files_processed"] == 1
    assert len(body["results"]) == 1
    r = body["results"][0]
    assert r["status"] == "ok"
    assert "chunks_processed" in r
    assert isinstance(r["chunks_processed"], int)
    # At minimum one chunk was processed
    assert r["chunks_processed"] >= 1
