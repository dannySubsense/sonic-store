# Architecture: Horizon 1 — Derivative Features
**Version:** 1.0
**Date:** 2026-04-16
**Status:** APPROVED FOR IMPLEMENTATION
**Author:** @architect

---

## 1. Scope Recap

Horizon 1 extends SonicStore in two directions without replacing or restructuring any existing module. Layer 1 is widened: seven new acoustic features are added to the output of `extract_features()` in `src/features/engine.py`. Layer 2 is introduced: a new standalone module (`src/features/indicators.py`) computes nine temporal indicators from the history ring on each cycle. A new prompt builder function (`build_prompt_v2`) replaces the call inside `GenerationEngine` while leaving the original `build_prompt` callable intact. The WebSocket broadcast payload is extended to carry both layers; REST endpoints and the store interface are untouched. The `SHOULD`-add Layer 1 features (`cens`, `percussive_ratio`) are explicitly out of scope per TD decision OQ-01; the nine SHOULD Layer 2 indicators are out of scope per TD decision OQ-02; Layer 3, Layer 4, session logging, UI restructuring, and store schema changes are out of scope. All design decisions from `01-REQUIREMENTS.md` open questions OQ-01 through OQ-07 are resolved by Technical Director decisions transmitted with this task brief and are treated as locked.

---

## 2. Module Map

### New Files

| File | Purpose |
|------|---------|
| `src/features/indicators.py` | Layer 2 computation module; exposes `compute_indicators(history, window)` returning the nine MUST temporal indicators |
| `src/features/thresholds.py` | Named constants for all trajectory descriptor thresholds used by `build_prompt_v2` |
| `src/generation/prompt_v2.py` | Prompt builder v2; exposes `build_prompt_v2(features, indicators)` and re-exports `build_prompt` for backward compatibility |
| `tests/test_indicators.py` | Unit tests for all nine Layer 2 indicators including cold-start, edge cases |
| `tests/test_prompt_v2.py` | Unit tests for `build_prompt_v2` including trajectory descriptor presence and cold-start fallback |

### Modified Files

| File | Modification |
|------|-------------|
| `src/features/engine.py` | Add seven new Layer 1 keys to the return dict of `extract_features()`; no signature change |
| `src/generation/engine.py` | Change the generation loop to call `store.get_history(N)` then `compute_indicators()` then `build_prompt_v2()`; retain `build_prompt` import for fallback |
| `src/api/app.py` | Modify both `mic_loop` AND the `demo_start` endpoint. In `mic_loop`: extend the broadcast call to compute and include indicators in the WS frame; broadcast dict shape changes from `{"type": "features", "data": fv}` to `{"type": "features", "data": fv, "indicators": ind_or_none}`. In `demo_start`: additionally changed to iterate all chunks (not just `next(chunks)`) so history accumulates to ≥N across each multi-chunk file. |
| `ui/app.js` | Consume new WS frame shape; render regime pill and trend arrow from `indicators` field; handle `null` indicators with a "warming up" state |
| `tests/test_features.py` | Add assertions for the seven new Layer 1 keys: shape, type, and range checks |

### Unmodified Files (confirmed no change needed)

| File | Reason |
|------|--------|
| `src/store/base.py` | Store interface unchanged |
| `src/store/dict_store.py` | Store implementation unchanged |
| `src/store/redis_store.py` | Store implementation unchanged |
| `src/generation/prompt.py` | `build_prompt()` preserved verbatim for backward compat |
| `src/api/websocket.py` | `ConnectionManager.broadcast()` is payload-agnostic |
| `src/api/routes_features.py` | REST consumers unchanged |
| `src/api/routes_analyze.py` | Unchanged |
| `src/features/key_detection.py` | Unchanged |

---

## 3. Layer 1 Widening Design

### 3.1 Updated `extract_features()` Contract

Signature is unchanged:

```python
def extract_features(
    audio: np.ndarray,
    sr: int = 22050,
    source: str = "mic",
    chunk_index: int | None = None,
) -> FeatureVector:
```

The return dict gains seven new keys. All 13 existing keys remain present and unchanged in name, type, and shape.

**New keys added to FeatureVector:**

| Key | Type | Shape / Range | Description |
|-----|------|--------------|-------------|
| `spectral_rolloff_hz` | `float` | scalar, `(0, sr/2]` Hz | Frequency below which 85% of spectral energy lies |
| `spectral_flux` | `float` | `[0.0, 1.0]` normalized | Mean frame-to-frame spectral magnitude difference |
| `spectral_contrast` | `list[float]` | length 7 | Per-octave subband log contrast values |
| `zero_crossing_rate` | `float` | `[0.0, 1.0]` normalized | Mean ZCR over frames, normalized to `[0, 1]` |
| `mfcc` | `list[float]` | length 13 | Mean of coefficients 1–13 over time frames |
| `harmonic_ratio` | `float` | `[0.0, 1.0]` | `H_energy / (H_energy + P_energy)` from HPSS |
| `tonnetz` | `list[float]` | length 6 | Tonal centroid features (fifths, minor thirds, major thirds) |

### 3.2 Computation Per Feature

All calls below receive `y=audio, sr=sr` unless noted. Default librosa hop and window parameters are used throughout; deviations are justified where noted.

**`spectral_rolloff_hz`**

```python
rolloff_matrix = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)
spectral_rolloff_hz = float(rolloff_matrix.mean())
```

Uses librosa default `roll_percent=0.85` (85th percentile). No deviation from default. Outputs a scalar float in Hz.

**`spectral_flux`**

Librosa does not expose a single `spectral_flux` function that returns a scalar. Compute from the STFT magnitude matrix:

```python
S = np.abs(librosa.stft(audio))          # shape (1 + n_fft/2, T)
flux_frames = np.sum(np.diff(S, axis=1) ** 2, axis=0)  # shape (T-1,)
raw_flux = float(flux_frames.mean())
spectral_flux = float(np.clip(raw_flux / FLUX_NORM_DIVISOR, 0.0, 1.0))
```

`FLUX_NORM_DIVISOR` is a constant defined in `src/features/thresholds.py` (default `1.0`; set empirically after benchmark; see Section 5). The STFT uses librosa defaults: `n_fft=2048`, `hop_length=512`, `window='hann'`. These match the parameters used for `mel_spectrogram` already in the engine, so the STFT can be computed once and reused for both if desired (optimization opportunity, not required for v1). For silent audio, `S` is near-zero, `flux_frames` is near-zero, and `spectral_flux` returns `0.0` — no divide-by-zero.

**`spectral_contrast`**

```python
contrast_matrix = librosa.feature.spectral_contrast(y=audio, sr=sr, n_bands=6)
spectral_contrast = contrast_matrix.mean(axis=1).tolist()  # length 7
```

`n_bands=6` produces 7 values (6 bands + 1 valley). Librosa default. The output is NOT normalized — it is log-ratio in dB, typically in the range `[0, 40]` per band. Downstream consumers (UI, prompt builder v2) must be aware it is not bounded to `[0, 1]`. No normalization is applied here to preserve interpretability.

**`zero_crossing_rate`**

```python
zcr_matrix = librosa.feature.zero_crossing_rate(y=audio)
raw_zcr = float(zcr_matrix.mean())
# Practical max for music ~0.3; clamp to [0, 1]
zero_crossing_rate = float(np.clip(raw_zcr / 0.3, 0.0, 1.0))
```

Uses the same fixed-divisor normalization pattern already established in `engine.py` for `rms_energy` and `onset_strength`. Divisor `0.3` matches the practical upper bound for music; pure noise approaches `0.5` ZCR which would be clipped to `1.0`. Justified: consistent with existing normalization pattern.

**`mfcc`**

```python
mfcc_matrix = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
mfcc = mfcc_matrix.mean(axis=1).tolist()  # length 13, coefficients 1-13
```

`n_mfcc=13` is the spec requirement and the Davis & Mermelstein (1980) standard. Librosa default `n_fft=2048`, `hop_length=512`, `n_mels=128` are used. These are consistent with `mel_spectrogram` parameters already in the engine. The zeroth coefficient (energy) is included as `mfcc[0]` for completeness; the requirements spec "coefficients 1-13" refers to the 13-element vector not the exclusion of coefficient zero. Output is unbounded floats (MFCC values are not normalized); the prompt builder v2 does not use MFCC directly in Horizon 1 (the `mfcc_delta` indicator is out of scope per OQ-02). This key is stored for downstream use.

**`harmonic_ratio`**

```python
harmonic, percussive = librosa.effects.hpss(audio)
h_energy = float(np.sum(harmonic ** 2))
p_energy = float(np.sum(percussive ** 2))
total_energy = h_energy + p_energy
if total_energy < 1e-8:
    harmonic_ratio = 0.5  # neutral default for silence / near-silence
else:
    harmonic_ratio = float(np.clip(h_energy / total_energy, 0.0, 1.0))
```

`librosa.effects.hpss` with default parameters uses median filtering on the power spectrogram. Default `kernel_size=31` for both harmonic and percussive filters. No deviation. The `total_energy < 1e-8` guard handles silent audio (all-zero input) without division by zero; returns `0.5` (neutral) as specified in the edge case table. This is the computationally expensive feature (HPSS runs two median filters over the STFT); per OQ-01 it is MUST but the roadmap benchmark slice will validate the latency on demo hardware before forge begins.

**`tonnetz`**

```python
# tonnetz requires harmonic audio for stable tonal centroid estimation
# Use harmonic component if available, else full audio
harmonic_for_tonnetz = harmonic if total_energy >= 1e-8 else audio
tonnetz_matrix = librosa.feature.tonnetz(y=harmonic_for_tonnetz, sr=sr)
tonnetz = tonnetz_matrix.mean(axis=1).tolist()  # length 6
```

`librosa.feature.tonnetz` internally computes chroma CQT. Using the harmonic component (already computed above for `harmonic_ratio`) as input suppresses percussive noise from the tonal centroid. This reuses a computation already performed and improves tonal feature quality. The six dimensions correspond to: fifths (2), minor thirds (2), major thirds (2). Output values are typically in `[-1, 1]` but are not clamped — the spec requires `list[float]` without bounds constraint. For silent audio (where harmonic separation yields near-zero), `tonnetz` values will be near-zero or NaN from chroma; add a guard:

```python
if any(np.isnan(t) or np.isinf(t) for t in tonnetz):
    tonnetz = [0.0] * 6
```

### 3.3 Code Reuse — Single STFT/HPSS Pass

The HPSS decomposition produces `harmonic` and `percussive` arrays. These can be reused:
- `harmonic_ratio` uses `harmonic` and `percussive` energy sums
- `tonnetz` uses `harmonic` as input
- `spectral_flux` uses `librosa.stft(audio)` — same STFT underlying HPSS

For v1, correctness is the priority. If the benchmark slice (Horizon 1 Slice 1) shows the 500ms budget is threatened, the optimization is to compute one STFT, derive HPSS from it, and pass the spectrogram to downstream feature calls. This is deferred to the benchmark outcome.

### 3.4 Edge Cases and Failure Modes

| Case | Behavior |
|------|---------|
| Silent audio (all zeros) | `spectral_flux = 0.0`, `harmonic_ratio = 0.5` (guard), `tonnetz = [0.0]*6` (guard), all others return zero or near-zero finite values |
| Impulse audio (single spike) | HPSS operates on power spectrogram; spike appears as broadband energy; all features return finite floats |
| `total_energy < 1e-8` in HPSS | `harmonic_ratio = 0.5`; `harmonic_for_tonnetz` falls back to `audio` |
| NaN / Inf in `tonnetz` | Replaced with `[0.0]*6` |
| NaN / Inf in any scalar feature | Caller should wrap `extract_features` in try/except for critical paths; engine already catches at the websocket level |

---

## 4. Layer 2 Indicator Module Design

### 4.1 Module: `src/features/indicators.py`

```python
import os
import numpy as np
from typing import Optional
from src.features.thresholds import (
    ENERGY_MOMENTUM_RISING_THRESHOLD,
    ENERGY_MOMENTUM_FALLING_THRESHOLD,
)

HORIZON1_WINDOW_N: int = int(os.getenv("HORIZON1_WINDOW_N", "10"))

IndicatorDict = dict  # keys defined below; values float | str | None

def compute_indicators(
    history: list[dict],
    window: int = HORIZON1_WINDOW_N,
) -> IndicatorDict:
    """Compute Layer 2 temporal indicators from the history ring.

    history: list of FeatureVector dicts, newest first (as returned by store.get_history()).
    window: number of recent entries to use. Clamped to len(history) and ring capacity (30).
    Returns a dict with keys: available, delta_bpm, bpm_volatility, energy_momentum,
    energy_regime, chroma_entropy, chroma_volatility, key_stability, spectral_trend,
    onset_regularity.
    If len(history) < window, returns {"available": False, ...all other keys: None}.
    """
```

### 4.2 Return Shape

```python
{
    "available": bool,               # False when len(history) < window
    "delta_bpm": float | None,
    "bpm_volatility": float | None,
    "energy_momentum": float | None,
    "energy_regime": str | None,     # "rising" | "falling" | "stable"
    "chroma_entropy": float | None,
    "chroma_volatility": float | None,
    "key_stability": float | None,
    "spectral_trend": float | None,
    "onset_regularity": float | None,
}
```

When `available` is `False`, all indicator keys are `None`. This is the canonical cold-start sentinel.

### 4.3 Window Clamping

```python
window = min(window, 30, len(history))
if len(history) < int(os.getenv("HORIZON1_WINDOW_N", "10")):
    return _cold_start_result()
```

The effective window is clamped to `min(HORIZON1_WINDOW_N, 30, len(history))`. If `len(history) < HORIZON1_WINDOW_N`, the function returns the cold-start result without any computation. If `HORIZON1_WINDOW_N > 30`, the env var is clamped to 30 (ring capacity). This prevents out-of-bounds access in all cases.

### 4.4 Per-Indicator Computation

The history ring is newest-first. To obtain a time-ordered window (oldest-first) for delta/regression computations:

```python
window_entries = history[:window]          # newest first, length = window
ordered = list(reversed(window_entries))   # oldest first, for correct delta direction
```

**`delta_bpm`** — tempo acceleration/deceleration

```python
bpm_series = np.array([e["bpm"] for e in ordered], dtype=float)
delta_bpm = _regression_delta(bpm_series)
```

`_regression_delta` implements the Davis & Mermelstein (1980) regression-weighted first derivative:

```
delta_f_t = sum(n * (f[t+n] - f[t-n]) for n in 1..N/2) / (2 * sum(n^2 for n in 1..N/2))
```

Applied to the full window, returning the derivative at the midpoint, which represents the average slope. Output: float (positive = accelerating, negative = decelerating, zero = stable).

**`bpm_volatility`** — rhythmic stability

```python
bpm_volatility = float(np.std(bpm_series))
```

Standard deviation over the window. Output: float >= 0. When all BPM values are identical, returns `0.0` — no divide-by-zero.

**`energy_momentum`** — slope of RMS energy trajectory

```python
energy_series = np.array([e["rms_energy"] for e in ordered], dtype=float)
x = np.arange(len(energy_series), dtype=float)
coeffs = np.polyfit(x, energy_series, 1)   # linear regression
energy_momentum = float(coeffs[0])          # slope coefficient
```

Linear regression slope over the window. Positive = building energy, negative = declining. Output: float. `np.polyfit` is numerically stable for small N.

**`energy_regime`** — macro dynamic classification

```python
if energy_momentum > ENERGY_MOMENTUM_RISING_THRESHOLD:
    energy_regime = "rising"
elif energy_momentum < ENERGY_MOMENTUM_FALLING_THRESHOLD:
    energy_regime = "falling"
else:
    energy_regime = "stable"
```

Thresholds imported from `src/features/thresholds.py`. Output: `"rising"` | `"falling"` | `"stable"`.

**`chroma_entropy`** — harmonic complexity of the most recent chunk

```python
# Use the current (most recent) chunk's chroma vector
current_chroma = np.array(history[0]["chroma"], dtype=float)   # history[0] = newest
chroma_sum = current_chroma.sum()
if chroma_sum < 1e-8:
    chroma_entropy = 0.0
else:
    p = current_chroma / chroma_sum
    p = np.clip(p, 1e-10, None)   # avoid log(0)
    chroma_entropy = float(-np.sum(p * np.log(p)))
```

Shannon entropy on the current chunk's chroma distribution. Maximum value is `log(12) ≈ 2.485` when all 12 pitch classes have equal energy. Output: float in `[0.0, log(12)]`.

`chroma_entropy` is computed from the current chunk's 12-element chroma vector (point-in-time Shannon entropy), per specs/05-SONIC-ALPHA.md L99. It is returned in the indicators dict because it is a derived quantity (not raw feature), enabling the UI and prompt builder to consume all Layer 2 signals from one place. `chroma_volatility` is the window-based dual that operates over the history ring. These are intentionally distinct indicators.

**`chroma_volatility`** — harmonic stability across window

```python
chroma_matrix = np.array([e["chroma"] for e in window_entries], dtype=float)  # (window, 12)
chroma_volatility = float(np.std(chroma_matrix, axis=0).mean())
```

Mean of per-pitch-class standard deviations over the window. Low = harmonically stable; high = rapid harmonic movement. Output: float >= 0.

**`key_stability`** — fraction of window in same key

```python
keys_in_window = [(e["key_pitch_class"], e["key_mode"]) for e in window_entries]
most_common_key = max(set(keys_in_window), key=keys_in_window.count)
count_matching = sum(1 for k in keys_in_window if k == most_common_key)
key_stability = float(count_matching / window)
```

Output: float in `[0.0, 1.0]`. When all N chunks share the same key, returns `1.0`. When key changes every chunk, returns `1/N`. No divide-by-zero (window is guaranteed >= 1 if we reach this point).

**`spectral_trend`** — direction of timbre movement

```python
centroid_series = np.array([e["spectral_centroid_hz"] for e in ordered], dtype=float)
spectral_trend = _regression_delta(centroid_series)
```

Same delta formula as `delta_bpm`. Positive = brightening timbre, negative = darkening. When centroid is constant, returns `0.0`. Output: float.

**`onset_regularity`** — rhythmic periodicity

```python
onset_series = np.array([e["onset_strength"] for e in ordered], dtype=float)
if np.std(onset_series) < 1e-8:
    onset_regularity = 0.0   # constant signal: no meaningful autocorrelation
else:
    autocorr = np.correlate(onset_series - onset_series.mean(),
                             onset_series - onset_series.mean(), mode='full')
    autocorr = autocorr[len(autocorr)//2:]   # positive lags only
    autocorr /= autocorr[0]                   # normalize: lag-0 = 1.0
    # Peak at lag 1 or 2 (beat-period for a 1-2s window) as regularity signal
    peak = float(np.max(autocorr[1:]))        # exclude lag-0
    onset_regularity = float(np.clip(peak, 0.0, 1.0))
```

Normalized autocorrelation peak at any non-zero lag. Returns `0.0` if no clear periodicity (e.g., constant series). Clipped to `[0.0, 1.0]`. If autocorrelation has no clear peak, `np.max` returns the largest value, which may be low — the clip ensures `0.0` lower bound and `1.0` upper bound. For the case where no peak exists, this correctly returns near-`0.0`. Output: float in `[0.0, 1.0]`.

### 4.5 Cold-Start Behavior

```python
def _cold_start_result() -> IndicatorDict:
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
```

Triggered when `len(history) < HORIZON1_WINDOW_N`. Zero history entries returns cold-start without any exception. Exactly `N-1` entries also returns cold-start. Exactly `N` entries returns populated indicators.

**Cold-start representations — two forms.** The cold-start result exists in two distinct forms depending on call site, and both must be handled correctly:

- *In-process form* (inside `compute_indicators`, `GenerationEngine`, and direct callers): `{"available": False, "delta_bpm": None, ..., "onset_regularity": None}` — a fully-keyed dict where `available` is `False` and all indicator keys are `None`. This is what `compute_indicators()` always returns; it is never `None`.
- *Wire form* (over WebSocket): `"indicators": null` — because `app.py`'s broadcast function collapses the in-process dict to `None` before serialisation: `ind_payload = indicators if indicators.get("available") else None`.

`build_prompt_v2(features, indicators)` is called from the `GenerationEngine` background thread, which receives the in-process form directly from `compute_indicators()`. It must therefore accept EITHER (a) the dict form with `available=False`, OR (b) `None` (defensive), and treat both as "cold-start — degrade to v1 prompt". The guard at §6.3 (`if indicators is None or not indicators.get("available", False)`) already satisfies this. The UI receives only the wire form (`null`) and never sees the dict form.

### 4.6 Determinism and Thread Safety

`compute_indicators` is a pure function: it takes a snapshot of history (a `list[dict]`) and returns a new dict. It does not write to any shared state. The history snapshot is obtained by calling `store.get_history(N)`, which is already thread-safe in both `DictStore` (uses `threading.Lock`) and `RedisStore` (atomic Redis reads). The snapshot itself is a new list; `compute_indicators` does not mutate it. No additional locking is required inside `compute_indicators`.

---

## 5. Thresholds Config Module

**File:** `src/features/thresholds.py`

```python
"""Named threshold constants for Horizon 1 trajectory descriptors.

All thresholds are importable constants, not environment variables.
They are initial calibration values; empirical tuning post-deployment
should result in updated values in this file (not scattered in code).
"""

# --- BPM delta thresholds ---
# Positive delta_bpm above this → "accelerating" descriptor
DELTA_BPM_THRESHOLD = 2.0
# Absolute value of negative delta_bpm above this → "decelerating" descriptor
# (delta_bpm < -DELTA_BPM_THRESHOLD triggers deceleration)

# --- Key stability thresholds ---
# key_stability above this → "harmonically stable" descriptor
KEY_STABLE_HIGH = 0.75
# key_stability below this → "shifting harmonically" descriptor
KEY_STABLE_LOW = 0.40

# --- Energy momentum thresholds ---
# energy_momentum slope above this → "rising" regime
ENERGY_MOMENTUM_RISING_THRESHOLD = 0.01
# energy_momentum slope below this → "falling" regime (negative)
ENERGY_MOMENTUM_FALLING_THRESHOLD = -0.01

# --- Spectral trend thresholds ---
# spectral_trend above this (Hz per step) → "brightening timbre" descriptor
SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50.0
# spectral_trend below this → "darkening timbre" descriptor
SPECTRAL_TREND_DARKENING_THRESHOLD = -50.0

# --- Spectral flux normalization ---
# Divisor for normalizing raw spectral flux to [0, 1].
# Calibrate empirically from benchmark; initial estimate assumes mean flux
# for typical music in the range 0-1.0 for normalized magnitudes.
FLUX_NORM_DIVISOR = 1.0
```

**Rationale for defaults:**
- `DELTA_BPM_THRESHOLD = 2.0`: A 2 BPM/chunk drift is musically meaningful acceleration; below 2 is measurement noise at the 2-second chunk cadence.
- `KEY_STABLE_HIGH = 0.75`: 7-8 of 10 chunks in the same key = tonally anchored.
- `KEY_STABLE_LOW = 0.40`: Fewer than 4 of 10 in the same key = active modulation.
- `ENERGY_MOMENTUM_RISING_THRESHOLD = 0.01`: Slope of 0.01 in normalized RMS (0-1 scale) per chunk = perceptible build. Zero is the neutral baseline.
- `SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50.0 Hz`: A 50 Hz drift per chunk in spectral centroid is a perceptible timbre shift at typical centroid ranges (1500-3500 Hz).
- `FLUX_NORM_DIVISOR = 1.0`: Placeholder; must be set after the Horizon 1 benchmark slice runs against real audio.

All thresholds should be reviewed after one session of play-testing on the demo hardware.

---

## 6. Prompt Builder v2 Design

### 6.1 Module: `src/generation/prompt_v2.py`

The v1 `build_prompt` function in `src/generation/prompt.py` is preserved verbatim. The v2 builder lives in a new file. `GenerationEngine` changes its import to use `build_prompt_v2` from this new module.

```python
from src.generation.prompt import build_prompt   # re-exported for backward compat
from src.features.thresholds import (
    DELTA_BPM_THRESHOLD,
    KEY_STABLE_HIGH,
    KEY_STABLE_LOW,
    SPECTRAL_TREND_BRIGHTENING_THRESHOLD,
    SPECTRAL_TREND_DARKENING_THRESHOLD,
)

def build_prompt_v2(
    features: dict,
    indicators: dict | None,
) -> str:
    """Build a MusicGen text prompt from Layer 1 features and Layer 2 indicators.

    When indicators is None or indicators["available"] is False,
    falls back to build_prompt(features) — identical to v1 behavior.
    Output is always a non-empty natural-language string with no newlines,
    JSON, or special tokens.
    """
```

### 6.2 Input Contract

- `features`: a FeatureVector dict (Layer 1). Must contain all 13 v1 keys plus the 7 new Layer 1 keys. Prompt builder uses: `bpm`, `key_pitch_class`, `key_mode`, `rms_energy`, `spectral_centroid_hz`.
- `indicators`: the dict returned by `compute_indicators()`, or `None`. If `None` or `indicators["available"] is False`, falls back to v1.

### 6.3 Cold-Start Fallback

```python
if indicators is None or not indicators.get("available", False):
    return build_prompt(features)
```

This exactly replicates v1 output format when history is insufficient (FR-03i, AC-07).

### 6.4 Descriptor Selection Logic

When indicators are available, the v2 builder constructs trajectory phrases before assembling the final string.

**Trajectory phrase assembly (order: energy → tempo → key → timbre):**

| Condition | Descriptor phrase | FR ref |
|-----------|------------------|--------|
| `energy_regime == "rising"` | `"building energy"` | FR-03a |
| `energy_regime == "falling"` | `"fading energy"` | FR-03b |
| `delta_bpm > DELTA_BPM_THRESHOLD` | `"accelerating"` | FR-03c |
| `delta_bpm < -DELTA_BPM_THRESHOLD` | `"decelerating"` | FR-03d |
| `key_stability > KEY_STABLE_HIGH` | `"harmonically stable in {key_name} {mode}"` | FR-03e |
| `key_stability < KEY_STABLE_LOW` | `"shifting harmonically"` | FR-03f |
| `spectral_trend > SPECTRAL_TREND_BRIGHTENING_THRESHOLD` | `"brightening timbre"` | FR-03g |
| `spectral_trend < SPECTRAL_TREND_DARKENING_THRESHOLD` | `"darkening timbre"` | FR-03h |

When no trajectory condition is triggered (all indicators in neutral zone), `trajectory_phrases` is empty and the output falls back to the v1 template extended only with the current indicators.

### 6.5 Output Template

```python
# Base components (same as v1)
energy_desc = _energy_descriptor(features["rms_energy"])
timbre_desc = _timbre_descriptor(features["spectral_centroid_hz"])
tempo_desc = _tempo_descriptor(features["bpm"])
key_name_str = _KEY_NAMES[features["key_pitch_class"] % 12]
mode = features["key_mode"]

# Trajectory component (new)
trajectory = ", ".join(trajectory_phrases)  # may be empty

if trajectory:
    prompt = (
        f"{energy_desc} {timbre_desc} musical accompaniment, "
        f"{tempo_desc}, {features['bpm']:.0f} BPM, {key_name_str} {mode}, "
        f"{trajectory}, "
        f"complementary to the input melody, instrumental"
    )
else:
    # No trajectory signals above threshold — use v1 format exactly
    prompt = (
        f"{energy_desc} {timbre_desc} musical accompaniment, "
        f"{tempo_desc}, {features['bpm']:.0f} BPM, {key_name_str} {mode}, "
        f"complementary to the input melody, instrumental"
    )
```

`prompt_v2.py` must NOT import these helpers from `src/generation/prompt.py` — the actual symbols are `_`-prefixed module-private names (`_KEY_NAMES`, `_tempo_descriptor`, `_energy_descriptor`, `_timbre_descriptor`), and importing private internals from another module is fragile. Instead, inline-duplicate the four small helpers directly in `prompt_v2.py`: the three three-line descriptor functions and the `_KEY_NAMES` list constant. No import from `prompt.py` for these symbols.

### 6.6 Output Invariants

- Always a non-empty `str`
- No newlines (`\n`)
- No JSON, no brackets, no special tokens
- Natural language prose
- Single sentence (comma-separated phrases)

These satisfy AC-08 and FR-03j.

### 6.7 GenerationEngine Call Site Change

In `src/generation/engine.py`, the generation loop changes from:

```python
# v1 (current)
from src.generation.prompt import build_prompt
...
prompt = build_prompt(features)
```

To:

```python
# v2
from src.generation.prompt_v2 import build_prompt_v2
from src.features.indicators import compute_indicators, HORIZON1_WINDOW_N
...
history = self._store.get_history(HORIZON1_WINDOW_N)
indicators = compute_indicators(history, window=HORIZON1_WINDOW_N)
prompt = build_prompt_v2(features, indicators)
```

The `get_latest()` call for the timestamp check is retained. The `get_history()` call is new and runs synchronously in the background thread — this is safe because `GenerationEngine` already runs in a `threading.Thread` (not the FastAPI async loop). `compute_indicators` is a pure Python/NumPy function well within the 50ms Layer 2 budget.

Full updated generation loop sequence:

```
1. time.sleep(GENERATION_INTERVAL)
2. features = store.get_latest()              # unchanged
3. check timestamp dedup                      # unchanged
4. history = store.get_history(HORIZON1_WINDOW_N)  # NEW
5. indicators = compute_indicators(history)   # NEW
6. prompt = build_prompt_v2(features, indicators)   # changed
7. clip = self._generate_clip(prompt, features)    # unchanged
8. output_queue.put(clip)                     # unchanged
```

---

## 7. WebSocket Payload Evolution

### 7.1 Old Payload Shape (v1)

```typescript
// FeatureMessage (server -> client)
{
  "type": "features",
  "data": FeatureVector      // Layer 1 only, 13 keys
}
```

### 7.2 New Payload Shape (v2)

```typescript
// FeatureMessage (server -> client, Horizon 1)
{
  "type": "features",
  "data": FeatureVector,            // Layer 1, now 20 keys (13 + 7 new)
  "indicators": IndicatorDict | null  // Layer 2, or null during warm-up
}
```

The `"indicators"` field is `null` when `compute_indicators` returns `{"available": False, ...}`. The UI must treat `null` indicators as the warm-up state.

### 7.3 Versioning Strategy

Additive approach — no WS protocol version field. Rationale:
- The only consumer of the WS is `ui/app.js`, which is in the same codebase and updated in this same forge sprint.
- Old consumers reading a `FeatureMessage` with an extra `"indicators"` key will ignore it — JSON additivity is the standard web pattern.
- Adding `"version": 2` would require version negotiation logic with no benefit given the single-client architecture.

The `"data"` key retains the same name; the FeatureVector dict grows from 13 to 20 keys but all 13 original keys remain.

### 7.4 Broadcast Call Site Change in `src/api/app.py`

In `mic_loop`, the broadcast line changes from:

```python
# v1
await manager.broadcast({"type": "features", "data": features})
```

To:

```python
# v2
from src.features.indicators import compute_indicators, HORIZON1_WINDOW_N
history = store.get_history(HORIZON1_WINDOW_N)
indicators = compute_indicators(history, window=HORIZON1_WINDOW_N)
ind_payload = indicators if indicators.get("available") else None
await manager.broadcast({
    "type": "features",
    "data": features,
    "indicators": ind_payload,
})
```

`store.get_history()` is a fast in-memory read (DictStore) or a Redis LRANGE (RedisStore). Both are synchronous and complete in milliseconds. `compute_indicators` is called directly on the asyncio event loop — not in `run_in_executor`. This is the locked decision: §9.3 shows Layer 2 computation is < 5ms on a 10-entry history (small NumPy arrays, no I/O), which is well within the event-loop budget. Wrapping it in `run_in_executor` would add thread-pool overhead with no benefit.

The `demo_start` endpoint in `app.py` also broadcasts features. It is updated in Section 7.4.1 below.

### 7.4.1 demo_start endpoint chunk iteration

**Current behavior (v1):** `next(chunks)` is called on the `load_and_chunk(str(wav_path))` generator, taking only the first 2-second slice from each WAV file. The rest of the generator is discarded. With 3-5 demo files, the history ring accumulates at most 3-5 entries per demo run — well below N=10 — so Layer 2 indicators remain `null` throughout the entire demo.

**New behavior (v2):** Iterate the full generator from `load_and_chunk(str(wav_path))` for each WAV file. For each chunk:

1. `features = extract_features(chunk, source="file")`
2. `store.write(features)`
3. `history = store.get_history(HORIZON1_WINDOW_N)`
4. `indicators = compute_indicators(history, window=HORIZON1_WINDOW_N)`
5. `ind_payload = indicators if indicators.get("available") else None`
6. `await manager.broadcast({"type": "features", "data": features, "indicators": ind_payload})`
7. `await asyncio.sleep(0.1)` (chunk-level pacing)

After all chunks in a file are processed, `await asyncio.sleep(0.5)` (file-level pacing) before advancing to the next file.

**Why:** With 3-5 demo WAV files at 10-20 seconds each (5-10 chunks per file at 2s per chunk), iterating all chunks yields 15-50 history entries per demo run — comfortably past N=10. Layer 2 indicators begin populating mid-demo rather than never populating. Horizon 1's regime pill, spectral arrow, and prompt trajectory phrases become visible during the demo.

**Chunk-level sleep rationale:** The 0.1s sleep between chunks within a file prevents broadcast flooding while ensuring continuous visual feedback in the UI dashboard — sparklines and the regime pill update chunk by chunk as history accumulates. The 0.5s inter-file gap is preserved to give the audience a perceivable boundary between source files.

**Response body:** The `/demo/start` response body retains one result entry per file (the `results` array shape is unchanged). A `chunks_processed: int` field is added to each per-file result entry for transparency. The top-level `files_processed` count is unchanged. This is an additive response body change; no breaking change to `/demo/start` consumers.

### 7.5 UI Handler Change

In `ui/app.js`, the WebSocket `onmessage` handler currently processes `{"type": "features", "data": fv}`. The updated handler:

```javascript
if (msg.type === "features") {
    updateFeatureDisplay(msg.data);           // existing, unchanged
    updateIndicatorDisplay(msg.indicators);   // new function, handles null
}
```

`updateIndicatorDisplay(null)` renders the "warming up" state for trend indicators (regime pill shows "—", direction arrow hidden or grayed). `updateIndicatorDisplay(indicators)` renders:
- Regime pill: `indicators.energy_regime` → colored label ("rising" = green, "falling" = red, "stable" = gray)
- Direction arrow for BPM: based on sign of `indicators.delta_bpm` vs `DELTA_BPM_THRESHOLD` (this threshold is known to the UI only for display; it does not need to match exactly — it reads the string `energy_regime` and float `delta_bpm`)
- Sparkline data: `msg.data.bpm` and `msg.data.rms_energy` accumulated client-side into a rolling buffer for the BPM and energy sparklines (the sparklines draw from the `data` field, not `indicators`)

The UI spec writer will define the exact visual presentation. This architecture defines only the data the UI receives.

---

## 8. Store Impact

Zero store schema change. Confirmed:

- `store.write(feature_vector)` — FeatureVector now contains 20 keys (13 + 7 new). This is additive. Both `DictStore` and `RedisStore` serialize to JSON and store transparently; the store implementations have no awareness of key names.
- `store.get_latest()` — returns the 20-key FeatureVector unchanged.
- `store.get_history(limit)` — returns a list of 20-key FeatureVectors unchanged.
- `store.ping()` — unchanged.
- The history ring capacity remains 30 entries. `HISTORY_MAX_ENTRIES = 30` is unchanged.
- Layer 2 indicators are never written to the store. They are computed fresh from the history ring on each cycle.
- `GET /features/latest` and `GET /features/history` return Layer 1 FeatureVectors (now 20 keys). The 7 new keys are additional data, not schema breaking. REST consumers receive richer data automatically.

---

## 9. Latency Budget Allocation

### 9.1 Current v1 Per-Chunk Budget

From `specs/02-ARCHITECTURE.md` Section 5:

| Stage | v1 Budget | Actual (estimated) |
|-------|-----------|-------------------|
| Mic capture | < 50ms | ~10ms |
| Feature extraction (`extract_features`) | < 500ms | ~100-200ms |
| Store write | < 5ms | < 5ms |
| WebSocket broadcast | < 20ms | < 10ms |
| **Feature-to-UI total** | **< 100ms** | **~150ms** |

### 9.2 Horizon 1 Layer 1 Budget

Target: `extract_features()` remains < 500ms. The new Layer 1 features add:

| New Feature | Estimated Additional Cost (CPU, demo hardware) |
|-------------|-----------------------------------------------|
| `spectral_rolloff_hz` | < 5ms (trivial frequency scan) |
| `spectral_flux` | < 10ms (STFT already computed; diff over frames) |
| `spectral_contrast` | < 15ms (octave subband computation) |
| `zero_crossing_rate` | < 5ms (scalar sum) |
| `mfcc` (n_mfcc=13) | < 20ms (mel filterbank + DCT; shares mel computation with `mel_spectrogram`) |
| `harmonic_ratio` (HPSS) | < 100ms (median filtering on STFT; most expensive new feature) |
| `tonnetz` | < 20ms (chroma CQT already computed; tonal centroid mapping) |
| **Total new Layer 1** | **< 175ms estimated** |

The benchmark slice will confirm. On the RTX 5090 demo hardware (fast CPU, no GPU involvement for librosa), these estimates are conservative; actual is likely < 100ms additional. v1 extraction was estimated at ~100-200ms; Horizon 1 target of combined < 500ms total provides significant headroom.

**If benchmark shows HPSS breaches the budget:** Per OQ-01 TD decision, `harmonic_ratio` downgrades to SHOULD via roadmap amendment. The architecture makes this cheap: `harmonic_ratio` is computed in a self-contained block in `extract_features()`. Removing it means deleting 10 lines and removing the `harmonic, percussive = librosa.effects.hpss(audio)` call. It does not affect any other feature computation (except `tonnetz` falls back to full audio input, which is already coded as the fallback).

### 9.3 Layer 2 Budget

`compute_indicators()` on 10 history entries of Layer 1 dicts:
- All operations are NumPy on small arrays (length 10-12)
- `np.polyfit` on N=10 points: < 1ms
- `np.correlate` on N=10 signal: < 1ms
- Total: < 5ms, well within the < 50ms target (AC-05)

Layer 2 is called twice per cycle: once in the generation loop (background thread) and once in the WebSocket broadcast (async event loop). Both are fast enough to run synchronously.

### 9.4 Prompt Builder v2

Pure string operations + threshold comparisons. < 1ms. Negligible.

### 9.5 End-to-End Budget (Horizon 1)

```
Mic capture                         ~50ms
Feature extraction (Layer 1 wide)   < 500ms  (target)
Layer 2 computation (WS path)       < 5ms
Store write                         < 5ms
WebSocket broadcast                 < 20ms
Feature-to-UI total                 < 600ms  (still well under 2s limit)

Generation path (background thread):
  Layer 2 computation               < 5ms
  build_prompt_v2                   < 1ms
  MusicGen generate                 < 4000ms (RTX 5090, CUDA FP16)
  Total generation cycle            ~3-7s
```

End-to-end < 2s feature loop preserved. The generation cycle (play → hear) is dominated by MusicGen (~3-6s), which is unchanged from v1.

---

## 10. Backward Compatibility Contract

The following contracts are explicitly guaranteed by this architecture:

**(a) Store consumers unaffected.** `DictStore` and `RedisStore` serialize FeatureVectors to JSON and deserialize transparently. Adding 7 keys to the FeatureVector is fully backward compatible. Any code reading `store.get_latest()` or `store.get_history()` will receive the new 20-key dicts without error; code that reads only specific keys (e.g., `features["bpm"]`) continues to work.

**(b) REST `/features/*` endpoints unaffected.** `GET /features/latest` and `GET /features/history` return FeatureVectors (now 20 keys). No status code, field name, or behavior change. API consumers that expect the 13 v1 keys will receive 7 extra keys; JSON additivity means no consumer breaks.

**(c) `build_prompt()` (v1) continues to work.** `src/generation/prompt.py` is not modified. `build_prompt(features)` called on a 20-key FeatureVector returns the same string format as before — it only reads `bpm`, `key_pitch_class`, `key_mode`, `rms_energy`, `spectral_centroid_hz`. AC-09 (v1 prompt builder on updated FeatureVector) is satisfied.

**(d) WebSocket frame shape changes.** The `"indicators"` field is new; old code ignoring unknown fields is unaffected. The `"data"` field shape changes from 13-key to 20-key dict — same additive guarantee applies. The `ui/app.js` update in this sprint is the only consumer and is updated simultaneously. The `demo_start` endpoint's visible behavior also changes: it now emits one broadcast frame per 2-second chunk (across all chunks in each file) rather than one frame per file. The `/demo/start` response body's `files_processed` count and `results` array shape are unchanged (one result entry per file); a `"chunks_processed": int` field is added to each per-file result entry. This is an additive response body change; no breaking change to `/demo/start` consumers.

**(e) GenerationEngine internal change.** The `build_prompt_v2` call is internal to the generation thread. No external interface changes. The `GeneratedClip.prompt` field continues to hold a string; it now holds a v2 string (which may include trajectory phrases) or a v1-format string (on cold start). The `GenerationMessage.data.prompt` field in the WebSocket output is unchanged in type.

---

## 11. Testing Strategy

### 11.1 Layer 1 — `tests/test_features.py` additions

For each of the seven new keys:
- **Shape test:** Given a 44100-sample sine wave, assert the key is present in the returned dict.
- **Type test:** Assert the value is `float` (scalar features) or `list` (vector features).
- **Range test:** Assert value is within documented range (e.g., `0.0 <= spectral_flux <= 1.0`).
- **Edge case — silence:** Given a zero array of 44100 samples, assert no exception and documented sentinel values (`harmonic_ratio == 0.5`, `tonnetz == [0.0]*6`, `spectral_flux == 0.0`).
- **Edge case — impulse:** Given a single-spike array, assert all seven values are finite floats (no NaN, no Inf).
- **Existing key preservation:** Assert all 13 v1 keys remain present and unchanged in type after adding Layer 1 widening.

### 11.2 Layer 2 — `tests/test_indicators.py` (new file)

**Cold-start tests:**
- Given empty history, `compute_indicators([], window=10)` returns `{"available": False, ...all None}` without exception.
- Given exactly 1 entry, returns `{"available": False, ...}`.
- Given exactly `N-1` entries, returns `{"available": False, ...}`.
- Given exactly `N` entries, returns `{"available": True, ...all float/str}`.

**Populated history tests (for each indicator):**
- Given 10 entries with monotonically increasing `bpm`, assert `delta_bpm > 0`.
- Given 10 entries with identical `bpm`, assert `bpm_volatility == 0.0` and `delta_bpm == 0.0`.
- Given 10 entries with monotonically increasing `rms_energy`, assert `energy_momentum > 0` and `energy_regime == "rising"`.
- Given 10 entries with constant `rms_energy`, assert `energy_regime == "stable"`.
- Given 10 entries with identical chroma vector (flat uniform), assert `chroma_volatility == 0.0`.
- Given 10 entries with identical chroma vector (single peak), assert `chroma_entropy < log(12)`.
- Given 10 entries all in the same key, assert `key_stability == 1.0`.
- Given 10 entries each in a different key, assert `key_stability == 1/N`.
- Given 10 entries with monotonically increasing `spectral_centroid_hz`, assert `spectral_trend > 0`.
- Given 10 entries with constant `onset_strength`, assert `onset_regularity == 0.0`.
- Given `HORIZON1_WINDOW_N > 30` set via env, assert function clamps window to 30 without error.

### 11.3 Prompt Builder v2 — `tests/test_prompt_v2.py` (new file)

**Cold-start fallback:**
- Given `indicators=None`, assert `build_prompt_v2(features, None)` returns same string as `build_prompt(features)`.
- Given `indicators={"available": False, ...}`, same assertion.
- Given 0-history indicators, assert no exception.

**Trajectory descriptor presence (AC-06):**
- Given `energy_regime="rising"`, assert output contains at least one of: "building", "increasing", "rising".
- Given `energy_regime="falling"`, assert output contains at least one of: "fading", "diminishing", "decreasing".
- Given `delta_bpm > DELTA_BPM_THRESHOLD`, assert output contains at least one of: "accelerating", "pushing tempo", "quickening".
- Given `delta_bpm < -DELTA_BPM_THRESHOLD`, assert output contains at least one of: "decelerating", "pulling back", "slowing".
- Given `key_stability > KEY_STABLE_HIGH` + specific key, assert output contains "harmonically stable".
- Given `spectral_trend > SPECTRAL_TREND_BRIGHTENING_THRESHOLD`, assert output contains "bright".

**Output invariants (AC-08):**
- Given any valid indicators dict, assert output is a non-empty `str`.
- Assert output contains no `\n`, no `{`, no `[`, no `"type":`.

**Snapshot tests:**
- Fixture history (10 entries of rising energy, same key, accelerating BPM) → assert prompt string equals expected snapshot string. This catches unintended descriptor changes.

### 11.4 Integration Test — GenerationEngine with v2 prompt

In `tests/test_generation.py`:
- Given a DictStore populated with 10 FeatureVector entries (fixture), mock `MusicGen.generate()`, start `GenerationEngine`, assert `output_queue.get()` produces a `GeneratedClip` whose `.prompt` contains trajectory descriptors.
- Given a DictStore with 0 entries, assert `GeneratedClip.prompt` matches v1 format (cold-start fallback).

---

## 12. Open Architectural Questions

None — all design decisions resolved.

The seven OQ items from `01-REQUIREMENTS.md` have been resolved by TD decisions OQ-01 through OQ-07 transmitted with this task brief:
- OQ-01: `harmonic_ratio` and `tonnetz` are MUST; benchmark slice validates before forge.
- OQ-02: Nine MUST Layer 2 indicators only; no SHOULD promotions.
- OQ-03: Thresholds in `src/features/thresholds.py` as named constants.
- OQ-04: Global `HORIZON1_WINDOW_N=10`, env-overridable.
- OQ-05: `compute_indicators` is a standalone module; two call sites (GenerationEngine + mic_loop).
- OQ-06: Layer 2 is derived, not persisted; WS payload extended to carry both layers.
- OQ-07: UI scope is regime pill + direction arrow for BPM + sparklines for BPM and energy.

`chroma_entropy` is computed from the current chunk's 12-element chroma vector (point-in-time Shannon entropy), per specs/05-SONIC-ALPHA.md L99. `chroma_volatility` is the window-based dual that operates over the history ring. These are intentionally distinct indicators.

---

*Architecture document by: @architect*
*Inputs: specs/horizon-1/01-REQUIREMENTS.md, specs/05-SONIC-ALPHA.md, specs/04-HORIZONS.md, specs/02-ARCHITECTURE.md, specs/00-DECISIONS.md, src/features/engine.py, src/features/key_detection.py, src/store/base.py + dict_store.py + redis_store.py, src/generation/prompt.py + engine.py, src/api/websocket.py + app.py + routes_features.py*
