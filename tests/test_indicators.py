"""Unit tests for Layer 2 temporal indicators (H1.S03).

Covers AC-03, AC-04, AC-05 and edge cases from specs/horizon-1/01-REQUIREMENTS.md.
All 16 tests map 1:1 to the H1.S03 test work items in specs/horizon-1/04-ROADMAP.md.
"""

import math
import os
import time
import numpy as np
import pytest

from src.features.indicators import compute_indicators, HORIZON1_WINDOW_N


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fv(
    bpm: float = 120.0,
    rms_energy: float = 0.3,
    chroma: list = None,
    key_pitch_class: int = 0,
    key_mode: str = "major",
    spectral_centroid_hz: float = 2000.0,
    onset_strength: float = 0.5,
) -> dict:
    """Build a minimal FeatureVector-like dict for indicator testing."""
    if chroma is None:
        chroma = [1.0 / 12] * 12
    return {
        "bpm": float(bpm),
        "rms_energy": float(rms_energy),
        "chroma": chroma,
        "key_pitch_class": int(key_pitch_class),
        "key_mode": key_mode,
        "spectral_centroid_hz": float(spectral_centroid_hz),
        "onset_strength": float(onset_strength),
    }


def make_history_newest_first(fvs_oldest_first: list) -> list:
    """Input oldest-first -> output newest-first (mimics store.get_history)."""
    return list(reversed(fvs_oldest_first))


# Expected indicator keys (9 + available)
INDICATOR_KEYS = [
    "delta_bpm",
    "bpm_volatility",
    "energy_momentum",
    "energy_regime",
    "chroma_entropy",
    "chroma_volatility",
    "key_stability",
    "spectral_trend",
    "onset_regularity",
]


# ---------------------------------------------------------------------------
# Cold-start tests (AC-04)
# ---------------------------------------------------------------------------

def test_cold_start_empty_history():
    """AC-04: empty history returns cold-start dict; no exception raised."""
    result = compute_indicators([], window=10)
    assert result["available"] is False
    for key in INDICATOR_KEYS:
        assert result[key] is None, f"Expected None for {key}, got {result[key]}"


def test_cold_start_one_entry():
    """AC-04: single entry returns cold-start (all None, available False)."""
    history = make_history_newest_first([make_fv()])
    result = compute_indicators(history, window=10)
    assert result["available"] is False
    for key in INDICATOR_KEYS:
        assert result[key] is None


def test_cold_start_n_minus_one():
    """AC-04: exactly N-1 entries with window=10 returns cold-start."""
    fvs = [make_fv() for _ in range(9)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is False
    for key in INDICATOR_KEYS:
        assert result[key] is None


# ---------------------------------------------------------------------------
# Warm (available) tests (AC-03)
# ---------------------------------------------------------------------------

def test_warm_exactly_n_entries():
    """AC-03: exactly N entries returns available=True with all 9 indicators non-None."""
    fvs = [make_fv() for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    for key in INDICATOR_KEYS:
        assert result[key] is not None, f"Expected non-None for {key}"


def test_delta_bpm_positive():
    """AC-03: monotonically increasing BPM yields delta_bpm > 0."""
    fvs = [make_fv(bpm=100 + i * 2) for i in range(10)]  # 100, 102, ..., 118
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["delta_bpm"] > 0, f"Expected positive delta_bpm, got {result['delta_bpm']}"


def test_delta_bpm_zero_constant_bpm():
    """AC-03 / Edge: constant BPM -> delta_bpm == 0.0 and bpm_volatility == 0.0."""
    fvs = [make_fv(bpm=120.0) for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["delta_bpm"] == pytest.approx(0.0, abs=1e-9)
    assert result["bpm_volatility"] == pytest.approx(0.0, abs=1e-9)


def test_energy_momentum_rising():
    """AC-03: monotonically increasing rms_energy -> energy_momentum > 0 and energy_regime == 'rising'."""
    fvs = [make_fv(rms_energy=i * 0.1) for i in range(10)]  # 0.0, 0.1, ..., 0.9
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["energy_momentum"] > 0, f"Expected positive energy_momentum, got {result['energy_momentum']}"
    assert result["energy_regime"] == "rising"


def test_energy_momentum_stable():
    """AC-03: constant rms_energy -> energy_regime == 'stable'."""
    fvs = [make_fv(rms_energy=0.3) for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["energy_regime"] == "stable"


def test_chroma_volatility_zero():
    """AC-03 / Edge: identical chroma vectors -> chroma_volatility == 0.0."""
    chroma = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    fvs = [make_fv(chroma=list(chroma)) for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["chroma_volatility"] == pytest.approx(0.0, abs=1e-9)


def test_chroma_entropy_uniform():
    """AC-03 / Edge: uniform chroma (all 1/12) -> chroma_entropy close to log(12)."""
    uniform_chroma = [1.0 / 12] * 12
    fvs = [make_fv(chroma=list(uniform_chroma)) for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    expected_entropy = math.log(12)  # ~2.4849
    assert result["chroma_entropy"] == pytest.approx(expected_entropy, rel=1e-4)


def test_key_stability_full():
    """AC-03: all N entries same key -> key_stability == 1.0."""
    fvs = [make_fv(key_pitch_class=5, key_mode="major") for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["key_stability"] == pytest.approx(1.0)


def test_key_stability_all_different():
    """AC-03 / Edge: each entry a unique key -> key_stability == 1/N."""
    keys = [
        (0, "major"), (1, "major"), (2, "major"), (3, "major"), (4, "major"),
        (5, "major"), (6, "major"), (7, "major"), (8, "major"), (9, "major"),
    ]
    fvs = [make_fv(key_pitch_class=pc, key_mode=mode) for pc, mode in keys]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["key_stability"] == pytest.approx(0.1)


def test_spectral_trend_positive():
    """AC-03: monotonically increasing spectral_centroid_hz -> spectral_trend > 0."""
    fvs = [make_fv(spectral_centroid_hz=1000 + i * 100) for i in range(10)]  # 1000, 1100, ..., 1900
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["spectral_trend"] > 0, f"Expected positive spectral_trend, got {result['spectral_trend']}"


def test_onset_regularity_constant_signal():
    """AC-03 / Edge: constant onset_strength -> onset_regularity == 0.0 (no variation)."""
    fvs = [make_fv(onset_strength=0.5) for _ in range(10)]
    history = make_history_newest_first(fvs)
    result = compute_indicators(history, window=10)
    assert result["available"] is True
    assert result["onset_regularity"] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Window clamping test (Edge Cases table)
# ---------------------------------------------------------------------------

def test_window_clamp_beyond_30():
    """Edge: window=50 with 30-entry history clamps to 30; no raise; available=True."""
    fvs = [make_fv() for _ in range(30)]
    history = make_history_newest_first(fvs)
    # Pass window=50 directly; the function clamps to min(50, 30, len(history)) = 30
    result = compute_indicators(history, window=50)
    assert result["available"] is True
    for key in INDICATOR_KEYS:
        assert result[key] is not None, f"Expected non-None for {key}"


# ---------------------------------------------------------------------------
# Latency test (AC-05)
# ---------------------------------------------------------------------------

def test_latency_under_50ms():
    """AC-05: Layer 2 computation over 30-entry history must be < 50ms per call."""
    fvs = [make_fv() for _ in range(30)]
    history = make_history_newest_first(fvs)

    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        compute_indicators(history, window=10)
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / iterations) * 1000
    assert mean_ms < 50.0, f"Mean latency {mean_ms:.2f}ms exceeds 50ms AC-05 budget"
