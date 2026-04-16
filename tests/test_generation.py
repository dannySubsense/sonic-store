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


# --- Mock helper ---

def _mock_load(engine):
    """Replace _load_model to inject a fake model without importing audiocraft."""
    engine._device = "cpu"
    engine._model = _FakeModel()
    engine.model_loaded = True
