"""Unit tests for DictStore: write, read latest, read history, history cap at 30."""

import threading
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


def test_concurrent_writes_no_race_condition() -> None:
    """Concurrent writes from 2 threads complete without race condition (spec S04 AC6)."""
    store = DictStore(history_max=30)
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def write_entries(start_offset: int) -> None:
        try:
            barrier.wait()  # synchronize both threads to start simultaneously
            for i in range(100):
                store.write(make_fv(chunk_index=start_offset + i))
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=write_entries, args=(0,))
    t2 = threading.Thread(target=write_entries, args=(1000,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Thread errors during concurrent writes: {errors}"
    history = store.get_history(limit=30)
    # History must be intact: correct length, each entry is a valid dict with expected keys
    assert len(history) == 30
    for entry in history:
        assert "chunk_index" in entry
        assert "bpm" in entry


# ---------------------------------------------------------------------------
# Redis integration tests — require local Redis at redis://localhost:6379/0
# Run with: make redis-up && pytest tests/test_store.py -v
# Skip automatically when Redis is not available.
# ---------------------------------------------------------------------------

_REDIS_URL = "redis://localhost:6379/0"
# Test-specific Redis keys — kept separate from any application keys
_TEST_LATEST_KEY = "features:latest"
_TEST_HISTORY_KEY = "features:history"


@pytest.fixture
def redis_store():
    """Create a RedisStore connected to local Redis; skip if Redis is unavailable."""
    from src.store.redis_store import RedisStore

    store = RedisStore(url=_REDIS_URL)
    if not store.ping():
        pytest.skip("Local Redis not available — skipping integration test")

    # Clean up test keys before each test to ensure isolation
    store._client.delete(_TEST_LATEST_KEY, _TEST_HISTORY_KEY)
    yield store
    # Clean up after each test
    store._client.delete(_TEST_LATEST_KEY, _TEST_HISTORY_KEY)


@pytest.mark.integration
def test_redis_ping_returns_true(redis_store) -> None:
    """RedisStore ping returns True with local Redis (spec S04 AC7)."""
    assert redis_store.ping() is True


@pytest.mark.integration
def test_redis_write_and_get_latest_round_trip(redis_store) -> None:
    """Write + get_latest round-trip via Redis (spec S04 AC8)."""
    fv = make_fv(chunk_index=99)
    fv["bpm"] = 142.0
    redis_store.write(fv)
    result = redis_store.get_latest()
    assert result is not None
    assert result["chunk_index"] == 99
    assert result["bpm"] == 142.0


@pytest.mark.integration
def test_redis_history_ring_cap_at_30(redis_store) -> None:
    """History ring is capped at 30 entries via Redis (spec S04 AC9)."""
    for i in range(35):
        redis_store.write(make_fv(chunk_index=i))
    history = redis_store.get_history(limit=30)
    assert len(history) == 30
    # Newest entry should be chunk_index 34 (lpush inserts at head)
    assert history[0]["chunk_index"] == 34
