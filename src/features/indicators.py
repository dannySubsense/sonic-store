"""Layer 2 temporal indicators computed from the FeatureVector history ring.

Pure function module: compute_indicators() reads a snapshot of history
and returns a new dict. Does not mutate history. Thread-safe by design.

See specs/horizon-1/02-ARCHITECTURE.md §4 for the full design and
specs/05-SONIC-ALPHA.md Layer 2 table for the musical/mathematical basis.
"""

import os
import numpy as np
from typing import Optional

from src.features.thresholds import (
    ENERGY_MOMENTUM_RISING_THRESHOLD,
    ENERGY_MOMENTUM_FALLING_THRESHOLD,
)

HORIZON1_WINDOW_N: int = int(os.getenv("HORIZON1_WINDOW_N", "10"))

IndicatorDict = dict  # keys: available + 9 indicators, see below


def _cold_start_result() -> IndicatorDict:
    """Return the canonical cold-start dict with all indicators None."""
    return {
        "available": False,
        "delta_bpm": None,
        "bpm_volatility": None,
        "energy_momentum": None,
        "energy_regime": None,
        "chroma_entropy": None,
        "chroma_volatility": None,
        "key_stability": None,
        "spectral_trend": None,
        "onset_regularity": None,
    }


def _regression_delta(series: np.ndarray) -> float:
    """Davis & Mermelstein (1980) regression-weighted first derivative.

    delta_f_t = sum(n * (f[t+n] - f[t-n]) for n in 1..N/2) / (2 * sum(n^2 for n in 1..N/2))

    Applied to the full series, returning the average slope.
    The series must be ordered oldest-first. A monotonically increasing series
    returns a positive value; a constant series returns 0.0; a monotonically
    decreasing series returns a negative value.
    """
    N = len(series)
    if N < 2:
        return 0.0
    half = N // 2
    if half < 1:
        return 0.0
    numerator = 0.0
    denominator = 0.0
    mid = N // 2
    for n in range(1, half + 1):
        left_idx = mid - n
        right_idx = mid + n - 1 if N % 2 == 0 else mid + n
        if left_idx < 0 or right_idx >= N:
            break
        # right is newer (larger index in oldest-first ordering) -> rising => positive
        numerator += n * (float(series[right_idx]) - float(series[left_idx]))
        denominator += n * n
    if denominator == 0:
        return 0.0
    return float(numerator / (2.0 * denominator))


def compute_indicators(
    history: list[dict],
    window: int = HORIZON1_WINDOW_N,
) -> IndicatorDict:
    """Compute 9 Layer 2 temporal indicators from the history ring.

    history: list of FeatureVector dicts, newest first (from store.get_history()).
    window: number of recent entries to use.

    Returns dict with keys: available, delta_bpm, bpm_volatility, energy_momentum,
    energy_regime, chroma_entropy, chroma_volatility, key_stability,
    spectral_trend, onset_regularity.

    Cold-start (len(history) < window): returns {"available": False, ...all None}.
    """
    # Clamp to ring capacity FIRST (spec §4.3)
    effective_window = min(window, 30)

    # Cold-start gate against the clamped value
    if len(history) < effective_window:
        return _cold_start_result()

    # Slice newest-first then reverse to oldest-first for delta/regression
    window_entries = history[:effective_window]
    ordered = list(reversed(window_entries))

    # --- delta_bpm ---
    bpm_series = np.array([e["bpm"] for e in ordered], dtype=float)
    delta_bpm = _regression_delta(bpm_series)

    # --- bpm_volatility ---
    bpm_volatility = float(np.std(bpm_series))

    # --- energy_momentum (linear regression slope) ---
    energy_series = np.array([e["rms_energy"] for e in ordered], dtype=float)
    x = np.arange(len(energy_series), dtype=float)
    if np.std(energy_series) < 1e-10:
        energy_momentum = 0.0
    else:
        coeffs = np.polyfit(x, energy_series, 1)
        energy_momentum = float(coeffs[0])

    # --- energy_regime ---
    # Use a 1-ULP-sized epsilon tolerance so that a polyfit slope that is
    # mathematically equal to the threshold but lands 1 ULP below due to
    # floating-point rounding still classifies correctly (rising/falling).
    _EPS = 1e-12
    if energy_momentum >= ENERGY_MOMENTUM_RISING_THRESHOLD - _EPS:
        energy_regime = "rising"
    elif energy_momentum <= ENERGY_MOMENTUM_FALLING_THRESHOLD + _EPS:
        energy_regime = "falling"
    else:
        energy_regime = "stable"

    # --- chroma_entropy (point-in-time, current chunk) ---
    current_chroma = np.array(history[0]["chroma"], dtype=float)
    chroma_sum = current_chroma.sum()
    if chroma_sum < 1e-8:
        chroma_entropy = 0.0
    else:
        p = current_chroma / chroma_sum
        p = np.clip(p, 1e-10, None)
        chroma_entropy = float(-np.sum(p * np.log(p)))

    # --- chroma_volatility (window-based) ---
    chroma_matrix = np.array([e["chroma"] for e in window_entries], dtype=float)
    chroma_volatility = float(np.std(chroma_matrix, axis=0).mean())

    # --- key_stability ---
    keys_in_window = [(e["key_pitch_class"], e["key_mode"]) for e in window_entries]
    most_common_key = max(set(keys_in_window), key=keys_in_window.count)
    count_matching = sum(1 for k in keys_in_window if k == most_common_key)
    key_stability = float(count_matching / effective_window)

    # --- spectral_trend (same formula as delta_bpm, applied to centroid series) ---
    centroid_series = np.array([e["spectral_centroid_hz"] for e in ordered], dtype=float)
    spectral_trend = _regression_delta(centroid_series)

    # --- onset_regularity (normalized autocorrelation peak) ---
    onset_series = np.array([e["onset_strength"] for e in ordered], dtype=float)
    if np.std(onset_series) < 1e-8:
        onset_regularity = 0.0
    else:
        centered = onset_series - onset_series.mean()
        autocorr_full = np.correlate(centered, centered, mode='full')
        autocorr = autocorr_full[len(autocorr_full) // 2:]
        if autocorr[0] == 0:
            onset_regularity = 0.0
        else:
            autocorr = autocorr / autocorr[0]
            peak = float(np.max(autocorr[1:])) if len(autocorr) > 1 else 0.0
            onset_regularity = float(np.clip(peak, 0.0, 1.0))

    return {
        "available": True,
        "delta_bpm": delta_bpm,
        "bpm_volatility": bpm_volatility,
        "energy_momentum": energy_momentum,
        "energy_regime": energy_regime,
        "chroma_entropy": chroma_entropy,
        "chroma_volatility": chroma_volatility,
        "key_stability": key_stability,
        "spectral_trend": spectral_trend,
        "onset_regularity": onset_regularity,
    }
