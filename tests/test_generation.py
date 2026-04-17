"""Tests for GenerationEngine with mocked MusicGen (no GPU required)."""

import queue
import time

import numpy as np
import pytest

from src.generation.engine import GeneratedClip, GenerationEngine
from src.store.dict_store import DictStore


# --- Helpers ---

def _make_feature_vector(bpm=120.0, key_pitch_class=2, key_mode="minor",
                         rms_energy=0.5, spectral_centroid_hz=3000.0) -> dict:
    """Return a minimal valid FeatureVector dict for testing."""
    return {
        "timestamp": int(time.time() * 1000),
        "chunk_index": 0,
        "source": "file",
        "duration_seconds": 2.0,
        "chroma": [0.1] * 12,
        "bpm": bpm,
        "key_pitch_class": key_pitch_class,
        "key_mode": key_mode,
        "rms_energy": rms_energy,
        "spectral_centroid_hz": spectral_centroid_hz,
        "onset_strength": 0.3,
        "mel_spectrogram": [[0.0] * 10] * 128,
        "waveform_display": [0.0] * 2048,
    }


class _FakeModel:
    """Mock MusicGen model that returns a silence tensor."""

    def set_generation_params(self, **kwargs):
        pass

    def generate(self, prompts):
        import torch
        # Return silence: shape (1, 1, 320000) = 10 seconds at 32kHz
        return torch.zeros(1, 1, 320000)

    def half(self):
        return self

    def to(self, device):
        return self


# --- Tests ---

def test_engine_starts_without_raising(monkeypatch):
    """Test 1: Engine starts and runs its background thread."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    engine = GenerationEngine(store=store, interval=0.5)
    engine.start()
    assert engine._running is True
    assert engine._thread is not None
    time.sleep(1.0)  # let it run a cycle
    engine.stop()


def test_engine_no_output_when_store_empty(monkeypatch):
    """Test 2: When store has no features, engine loops without producing output."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.5)
    engine.start()
    time.sleep(2.0)
    engine.stop()
    assert out_q.empty(), "Expected no output when store is empty"


def test_engine_produces_clip_when_features_exist(monkeypatch):
    """Test 3: Engine produces a GeneratedClip when store has features."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    store.write(_make_feature_vector())
    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.5)
    engine.start()

    # Wait up to 5 seconds for a clip
    clip = None
    try:
        clip = out_q.get(timeout=5.0)
    except queue.Empty:
        pass
    engine.stop()

    assert clip is not None, "Expected a GeneratedClip in output queue"
    assert isinstance(clip, GeneratedClip)


def test_generated_clip_has_valid_audio_b64(monkeypatch):
    """Test 4: GeneratedClip.audio_b64 is a non-empty base64 string."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    store.write(_make_feature_vector())
    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.5)
    engine.start()

    clip = out_q.get(timeout=5.0)
    engine.stop()

    assert isinstance(clip.audio_b64, str)
    assert len(clip.audio_b64) > 100, "audio_b64 should be a substantial base64 string"

    # Verify it's valid base64
    import base64
    decoded = base64.b64decode(clip.audio_b64)
    assert len(decoded) > 0


def test_generated_clip_prompt_contains_instrumental(monkeypatch):
    """Test 5: GeneratedClip.prompt is a non-empty string containing 'instrumental'."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    store.write(_make_feature_vector())
    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.5)
    engine.start()

    clip = out_q.get(timeout=5.0)
    engine.stop()

    assert isinstance(clip.prompt, str)
    assert len(clip.prompt) > 0
    assert "instrumental" in clip.prompt


def test_engine_stops_cleanly(monkeypatch):
    """Test 6: Engine stops without hanging when stop() is called."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    engine = GenerationEngine(store=store, interval=0.5)
    engine.start()
    assert engine._running is True

    engine.stop()
    assert engine._running is False
    assert engine._thread is None


def test_generation_v2_prompt_with_history(monkeypatch):
    """Test 7: With 10 rising-energy entries, GeneratedClip.prompt contains a trajectory descriptor."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    # Seed 10 entries with monotonically rising rms_energy (0.10 -> 0.55)
    # and a fixed key so key_stability=1.0 -> "harmonically stable" also fires.
    # Use distinct timestamps so the engine doesn't skip on dedup.
    base_ts = int(time.time() * 1000)
    for i in range(10):
        fv = _make_feature_vector(
            rms_energy=round(0.10 + i * 0.05, 2),
            key_pitch_class=2,
            key_mode="minor",
        )
        fv["timestamp"] = base_ts + i
        store.write(fv)

    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.1)
    engine.start()

    clip = None
    try:
        clip = out_q.get(timeout=10.0)
    except queue.Empty:
        pass
    engine.stop()

    assert clip is not None, "Expected a GeneratedClip in output queue"
    assert isinstance(clip, GeneratedClip)

    trajectory_phrases = [
        "building", "rising", "accelerating", "harmonically stable", "brightening",
    ]
    prompt_lower = clip.prompt.lower()
    assert any(phrase in prompt_lower for phrase in trajectory_phrases), (
        f"Expected at least one trajectory descriptor in prompt, got: {clip.prompt!r}"
    )


def test_generation_v2_cold_start_prompt(monkeypatch):
    """Test 8: With only 1 history entry (<N=10), prompt uses v1 fallback format."""
    monkeypatch.setattr(
        "src.generation.engine.GenerationEngine._load_model",
        lambda self: _mock_load(self),
    )
    store = DictStore()
    # Single entry: get_latest() is non-None but history length < 10 -> cold-start
    fv = _make_feature_vector(key_pitch_class=2, key_mode="minor")
    store.write(fv)

    out_q = queue.Queue()
    engine = GenerationEngine(store=store, output_queue=out_q, interval=0.1)
    engine.start()

    clip = None
    try:
        clip = out_q.get(timeout=10.0)
    except queue.Empty:
        pass
    engine.stop()

    assert clip is not None, "Expected a GeneratedClip in output queue"
    assert isinstance(clip, GeneratedClip)

    # v1 format must contain these strings
    assert "musical accompaniment" in clip.prompt, (
        f"Expected 'musical accompaniment' in cold-start prompt, got: {clip.prompt!r}"
    )
    assert "instrumental" in clip.prompt, (
        f"Expected 'instrumental' in cold-start prompt, got: {clip.prompt!r}"
    )
    # key_pitch_class=2 -> "D", mode="minor"
    assert "D" in clip.prompt, (
        f"Expected key name 'D' in cold-start prompt, got: {clip.prompt!r}"
    )

    # Must NOT contain v2-only trajectory phrases
    v2_only_phrases = ["building", "fading", "accelerating", "decelerating",
                       "harmonically stable", "shifting harmonically",
                       "brightening timbre", "darkening timbre"]
    for phrase in v2_only_phrases:
        assert phrase not in clip.prompt, (
            f"Cold-start prompt should not contain v2 trajectory phrase {phrase!r}, "
            f"got: {clip.prompt!r}"
        )


# --- Mock helper ---

def _mock_load(engine):
    """Replace _load_model to inject a fake model without importing audiocraft."""
    engine._device = "cpu"
    engine._model = _FakeModel()
    engine.model_loaded = True
