"""Unit tests for DictStore: write, read latest, read history, history cap at 30."""

import pytest

from src.store.dict_store import DictStore


def make_fv(chunk_index: int = 0) -> dict:
    """Minimal FeatureVector-shaped dict for testing."""
    return {
        "timestamp": 1000000 + chunk_index,
        "chunk_index": chunk_index,
        "bpm": 120.0,
        "key_pitch_class": 0,
        "key_mode": "major",
        "rms_energy": 0.3,
        "spectral_centroid_hz": 2000.0,
        "onset_strength": 0.5,
        "chroma": [0.0] * 12,
        "mel_spectrogram": [[0.0]],
        "waveform_display": [0.0] * 2048,
        "source": "file",
        "duration_seconds": 2.0,
    }


def test_get_latest_empty_store() -> None:
    store = DictStore()
    assert store.get_latest() is None


def test_write_and_get_latest() -> None:
    store = DictStore()
    fv = make_fv(chunk_index=0)
    store.write(fv)
    result = store.get_latest()
    assert result is not None
    assert result["chunk_index"] == 0


def test_get_latest_returns_most_recent() -> None:
    store = DictStore()
    store.write(make_fv(chunk_index=0))
    store.write(make_fv(chunk_index=1))
    store.write(make_fv(chunk_index=2))
    result = store.get_latest()
    assert result["chunk_index"] == 2


def test_get_history_empty() -> None:
    store = DictStore()
    assert store.get_history() == []


def test_get_history_order_newest_first() -> None:
    store = DictStore()
    for i in range(5):
        store.write(make_fv(chunk_index=i))
    history = store.get_history()
    indices = [fv["chunk_index"] for fv in history]
    assert indices == sorted(indices, reverse=True), (
        f"History should be newest-first, got indices {indices}"
    )


def test_get_history_limit() -> None:
    store = DictStore()
    for i in range(10):
        store.write(make_fv(chunk_index=i))
    history = store.get_history(limit=3)
    assert len(history) == 3


def test_history_cap_at_30() -> None:
    """Writing 35 entries should only keep the 30 most recent."""
    store = DictStore(history_max=30)
    for i in range(35):
        store.write(make_fv(chunk_index=i))
    history = store.get_history(limit=30)
    assert len(history) == 30
    # Newest should be chunk_index 34
    assert history[0]["chunk_index"] == 34
    # Oldest in history should be chunk_index 5 (35 - 30 = 5)
    oldest_index = history[-1]["chunk_index"]
    assert oldest_index == 5, f"Expected oldest to be 5, got {oldest_index}"


def test_history_cap_exact_30() -> None:
    """Writing exactly 30 entries should keep all 30."""
    store = DictStore(history_max=30)
    for i in range(30):
        store.write(make_fv(chunk_index=i))
    history = store.get_history()
    assert len(history) == 30


def test_ping_returns_true() -> None:
    store = DictStore()
    assert store.ping() is True


def test_write_round_trips_values() -> None:
    store = DictStore()
    fv = make_fv(chunk_index=42)
    fv["bpm"] = 137.5
    store.write(fv)
    result = store.get_latest()
    assert result["bpm"] == 137.5
    assert result["chunk_index"] == 42


def test_history_limit_respects_max() -> None:
    """Requesting limit > history_max should be capped at history_max."""
    store = DictStore(history_max=10)
    for i in range(10):
        store.write(make_fv(chunk_index=i))
    history = store.get_history(limit=50)
    assert len(history) <= 10
