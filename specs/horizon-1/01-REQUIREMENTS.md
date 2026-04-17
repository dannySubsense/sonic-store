# Requirements: Horizon 1 — Derivative Features

**Version:** 1.1
**Date:** 2026-04-16
**Status:** APPROVED — all open questions resolved by Technical Director
**Author:** Requirements Analyst (@requirements-analyst)

---

## Summary

Horizon 1 expands SonicStore's feature intelligence in two directions: (a) widening Layer 1 by adding established librosa features not yet extracted from each audio chunk, and (b) introducing Layer 2 by computing temporal indicators from the existing 30-entry history ring. The v1 prompt builder (static mapping table) is replaced by a v2 prompt builder that incorporates trajectory descriptors derived from Layer 2 indicators. No new ML models, no new storage infrastructure, and no Layer 3 or Layer 4 signals are in scope.

---

## User Stories

### US-01: Richer instantaneous feature extraction (Layer 1 widening)

As a musician using SonicStore,
I want the system to extract a broader set of acoustic features from each audio chunk,
so that the AI has more dimensions of my playing available for prompt construction.

### US-02: Temporal trajectory indicators (Layer 2 computation)

As a musician using SonicStore,
I want the system to compute momentum, volatility, and regime indicators from my recent playing history,
so that the AI can respond to where my music is going, not just where it is.

### US-03: Trajectory-aware prompt generation (Prompt Builder v2)

As a musician using SonicStore,
I want the AI generation prompt to describe musical trajectory (accelerating, building, stable, brightening),
so that the generated audio responds to the arc of my performance rather than a single frozen snapshot.

### US-04: Trend indicators visible in the UI

As a demo viewer or musician,
I want to see trajectory indicators (direction, trend, stability) alongside the current feature values,
so that I can see visually that the system understands the direction of my playing.

### US-05: Backward-compatible FeatureVector

As a developer of SonicStore,
I want existing consumers of the FeatureVector (WebSocket, UI, GenerationEngine) to continue operating without modification,
so that Horizon 1 does not break the v1 data pipeline.

---

## Functional Requirements

### FR-01: Layer 1 Feature Additions (MUST)

The following features MUST be extracted from each audio chunk and included in the FeatureVector. All are available in librosa with no new dependencies. They are defined in specs/05-SONIC-ALPHA.md Layer 1 table.

| Feature Key | Source | Output Shape/Type | Notes |
|-------------|--------|-------------------|-------|
| `spectral_rolloff_hz` | `librosa.feature.spectral_rolloff` | float, Hz | Frequency below which 85% of energy lies |
| `spectral_flux` | Frame-to-frame spectral difference | float, normalized 0-1 | Mean of $\sum_k (\|X_t[k]\| - \|X_{t-1}[k]\|)^2$ over frames |
| `spectral_contrast` | `librosa.feature.spectral_contrast` | list[float], length 7 | One value per octave subband |
| `zero_crossing_rate` | `librosa.feature.zero_crossing_rate` | float, normalized 0-1 | |
| `mfcc` | `librosa.feature.mfcc` | list[float], length 13 | Mean over time; 13 coefficients (indexed 0-12); the zeroth coefficient represents signal energy and is retained. |
| `harmonic_ratio` | `librosa.effects.hpss` | float, 0-1 | `H / (H + P)`, harmonic energy fraction |
| `tonnetz` | `librosa.feature.tonnetz` | list[float], length 6 | Tonal centroid (fifths, minor thirds, major thirds) |

The following Layer 1 features from specs/05-SONIC-ALPHA.md are SHOULD-add but are subject to open question OQ-01 (latency budget):

| Feature Key | Source | Notes |
|-------------|--------|-------|
| `cens` | `librosa.feature.chroma_cens` | Normalized/smoothed chroma; may be redundant with existing chroma |
| `percussive_ratio` | `librosa.effects.hpss` | Complement of `harmonic_ratio`; derivable, may be redundant |

### FR-02: Layer 2 Temporal Indicators (MUST)

The following temporal indicators MUST be computed from the history ring on each cycle. They are defined in specs/05-SONIC-ALPHA.md Layer 2 table and specs/04-HORIZONS.md candidate table.

| Indicator Key | Computed From | Method | Output Type |
|---------------|--------------|--------|-------------|
| `delta_bpm` | `bpm` history | Delta formula (Davis & Mermelstein 1980): regression-weighted first derivative | float |
| `bpm_volatility` | `bpm` history | `std(bpm[-N:])` over window N | float |
| `energy_momentum` | `rms_energy` history | Slope of linear regression over window N | float |
| `energy_regime` | `energy_momentum` | Classify as `"rising"` / `"falling"` / `"stable"` (threshold-based) | string |
| `chroma_entropy` | `chroma` (current chunk) | Shannon entropy: $-\sum p_i \log p_i$ where $p_i = C[i] / \sum C$ | float |
| `chroma_volatility` | `chroma` history | `mean(std(chroma[-N:], axis=0))` | float |
| `key_stability` | `key_pitch_class` + `key_mode` history | Fraction of last N chunks in the same key | float, 0-1 |
| `spectral_trend` | `spectral_centroid_hz` history | Delta formula applied to spectral centroid time series | float |
| `onset_regularity` | `onset_strength` history | Autocorrelation peak height at beat-period lag | float, 0-1 |

The following indicators from specs/05-SONIC-ALPHA.md Layer 2 are SHOULD-add but subject to OQ-02 (scope of v1 Horizon 1):

| Indicator Key | Notes |
|---------------|-------|
| `bpm_ma` | Simple moving average of BPM; useful for display |
| `energy_volatility` | `std(rms_energy[-N:])` |
| `key_change_rate` | Count of key changes in last N chunks |
| `spectral_bollinger` | Bollinger band position of centroid (requires `mu ± 2sigma` tracking) |
| `onset_density` | Count of onsets above threshold per window |
| `mfcc_delta` | Per-coefficient delta on MFCC history; 13-dim output |
| `harmonic_percussive_ratio` (trend) | Trend of `harmonic_ratio` over time |
| `flux_trend` | Delta formula on `spectral_flux` history |
| `dynamic_range` | `max - min` of `rms_energy` over window |

### FR-03: Prompt Builder v2 (MUST)

The v2 prompt builder MUST accept both Layer 1 features and Layer 2 indicators, and MUST incorporate trajectory descriptors where Layer 2 data is available.

**FR-03a:** When `energy_regime` is `"rising"`, the prompt MUST include a building/ascending energy descriptor (e.g., "building energy", "increasing intensity").

**FR-03b:** When `energy_regime` is `"falling"`, the prompt MUST include a winding-down descriptor (e.g., "fading energy", "diminishing intensity").

**FR-03c:** When `delta_bpm` is positive beyond a threshold (OQ-03), the prompt MUST include an acceleration descriptor (e.g., "accelerating", "pushing tempo").

**FR-03d:** When `delta_bpm` is negative beyond a threshold, the prompt MUST include a deceleration descriptor (e.g., "decelerating", "pulling back").

**FR-03e:** When `key_stability` is above a high threshold (OQ-03), the prompt MUST include a tonal stability descriptor (e.g., "harmonically stable in [key]").

**FR-03f:** When `key_stability` is below a low threshold, the prompt MUST include a harmonic movement descriptor (e.g., "shifting harmonically", "modulating").

**FR-03g:** When `spectral_trend` is positive beyond a threshold, the prompt MUST include a brightening timbre descriptor (e.g., "brightening timbre").

**FR-03h:** When `spectral_trend` is negative beyond a threshold, the prompt MUST include a darkening timbre descriptor (e.g., "darkening timbre").

**FR-03i:** When insufficient history is available (fewer chunks than the window size N), the v2 prompt builder MUST fall back to v1 behavior — no trajectory descriptors, same output format as the current `build_prompt()`.

**FR-03j:** The v2 prompt string MUST remain a valid MusicGen text prompt — natural language, single string, no structured data or special tokens.

### FR-04: Window Size Configurability (SHOULD)

The history window size N used for Layer 2 computation SHOULD be configurable (not hardcoded), with a documented default. Subject to OQ-04.

### FR-05: Layer 2 Availability Signaling (SHOULD)

The system SHOULD communicate to downstream consumers whether Layer 2 indicators are populated (i.e., whether enough history exists). This enables the UI to display a "warming up" state.

---

## Acceptance Criteria

### AC-01: Layer 1 feature keys present in FeatureVector

- [ ] Given a valid 2-second audio chunk, when `extract_features()` is called, then the returned dict contains all seven new keys: `spectral_rolloff_hz`, `spectral_flux`, `spectral_contrast`, `zero_crossing_rate`, `mfcc`, `harmonic_ratio`, `tonnetz`.
- [ ] `spectral_rolloff_hz` is a float in the range (0, sr/2] (i.e., 0 < value <= 11025 for sr=22050).
- [ ] `spectral_flux` is a float in the range [0.0, 1.0].
- [ ] `spectral_contrast` is a list of 7 floats.
- [ ] `zero_crossing_rate` is a float in the range [0.0, 1.0].
- [ ] `mfcc` is a list of 13 floats (coefficients indexed 0-12, zeroth coefficient is signal energy).
- [ ] `harmonic_ratio` is a float in the range [0.0, 1.0].
- [ ] `tonnetz` is a list of 6 floats.
- [ ] All 13 existing FeatureVector keys remain present and unchanged in type/shape.

### AC-02: Layer 1 extraction latency

- [ ] Given a 2-second audio chunk (44100 samples, float32), when `extract_features()` is called with all Layer 1 widening features included, then wall-clock execution time is below 500ms on the demo hardware (RTX 5090, 64GB RAM). This preserves headroom in the <2s end-to-end budget.

### AC-03: Layer 2 indicators computed from history

- [ ] Given a store with at least N entries in history, when Layer 2 computation is invoked, then the output contains all nine MUST indicators: `delta_bpm`, `bpm_volatility`, `energy_momentum`, `energy_regime`, `chroma_entropy`, `chroma_volatility`, `key_stability`, `spectral_trend`, `onset_regularity`.
- [ ] `delta_bpm` is a float (positive = accelerating, negative = decelerating, zero = stable).
- [ ] `bpm_volatility` is a float >= 0.
- [ ] `energy_momentum` is a float (positive = building, negative = declining).
- [ ] `energy_regime` is one of the strings `"rising"`, `"falling"`, or `"stable"`.
- [ ] `chroma_entropy` is a float in the range [0.0, log(12)] (max entropy for 12 pitch classes).
- [ ] `chroma_volatility` is a float >= 0.
- [ ] `key_stability` is a float in [0.0, 1.0] where 1.0 means all N chunks were in the same key.
- [ ] `spectral_trend` is a float (positive = brightening, negative = darkening).
- [ ] `onset_regularity` is a float in [0.0, 1.0] where 1.0 is perfectly periodic.

### AC-04: Layer 2 cold start (insufficient history)

- [ ] Given a store with fewer entries than the window size N, when Layer 2 computation is invoked, then it returns a result indicating indicators are unavailable (e.g., all None, or a `{"available": False}` dict) rather than raising an exception.
- [ ] Given a store with exactly 0 entries, when Layer 2 computation is invoked, then no exception is raised.

### AC-05: Layer 2 computation latency

- [ ] Given a history ring of 30 entries, when Layer 2 computation is invoked, then wall-clock execution time is below 50ms. Layer 2 is pure Python/NumPy; it must not be a meaningful contributor to the <2s budget.

### AC-06: Prompt builder v2 — trajectory descriptors present

- [ ] Given a history where `rms_energy` has been monotonically increasing for the last N chunks, when `build_prompt_v2()` is called, then the returned string contains at least one of: "building", "increasing", "rising energy", "intensifying".
- [ ] Given a history where `bpm` has been increasing for the last N chunks, when `build_prompt_v2()` is called, then the returned string contains at least one of: "accelerating", "pushing tempo", "quickening".
- [ ] Given a history where `bpm` has been decreasing for the last N chunks, when `build_prompt_v2()` is called, then the returned string contains at least one of: "decelerating", "pulling back", "slowing".
- [ ] Given a history where all N chunks share the same key, when `build_prompt_v2()` is called, then the returned string contains a key stability phrase such as "harmonically stable in [key name]".
- [ ] Given a history where `spectral_centroid_hz` has been increasing for the last N chunks, when `build_prompt_v2()` is called, then the returned string contains "bright" or "brightening".

### AC-07: Prompt builder v2 — cold start fallback

- [ ] Given fewer than N history entries, when `build_prompt_v2()` is called, then the returned string is identical in format to the v1 `build_prompt()` output (tempo descriptor + energy descriptor + timbre descriptor + BPM + key + suffix).
- [ ] Given 0 history entries, when `build_prompt_v2()` is called with only a current FeatureVector, then no exception is raised.

### AC-08: Prompt builder v2 — output is valid MusicGen input

- [ ] Given any valid history, when `build_prompt_v2()` is called, then the returned value is a non-empty Python `str`.
- [ ] The returned string contains no JSON, no newlines, no structured tokens or brackets — it is natural-language prose.

### AC-09: Existing FeatureVector consumers unaffected

- [ ] Given a FeatureVector produced by the updated `extract_features()`, when it is serialized and sent over the existing WebSocket endpoint, then the WebSocket client receives valid JSON.
- [ ] Given a FeatureVector produced by the updated `extract_features()`, when `build_prompt()` (v1) is called on it, then it returns a valid string without error. (v1 prompt builder must remain functional alongside v2.)

### AC-10: UI trend indicators displayed

- [ ] Given a page load after at least N chunks have been processed, when the user views the dashboard, then at least one trend indicator (direction arrow, spark line, or regime label) is visible for `energy_regime` and `delta_bpm`.
- [ ] Given fewer than N chunks processed, when the user views the dashboard, then trend indicators display a "warming up" or equivalent placeholder state rather than incorrect values.

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Silent audio chunk (all zeros) | `spectral_flux` = 0.0, `harmonic_ratio` = 0.0 or undefined (handle divide-by-zero), `chroma_entropy` returns valid value |
| Impulse audio (single spike) | All features return finite floats; no NaN or Inf values |
| History ring has exactly 1 entry | Layer 2 returns unavailable state; no index error |
| History ring has exactly N-1 entries | Layer 2 still returns unavailable state (incomplete window) |
| History ring has exactly N entries | Layer 2 computes and returns all MUST indicators |
| History window N larger than ring capacity (30) | System clamps N to ring capacity; no out-of-bounds access |
| All N BPM values are identical | `bpm_volatility` = 0.0, `delta_bpm` = 0.0; no divide-by-zero |
| All N chroma vectors are uniform (flat) | `chroma_entropy` = log(12) (maximum entropy); `chroma_volatility` = 0.0 |
| Key changes every chunk for N chunks | `key_stability` = 1/N (only 1 matching key in window) |
| `spectral_centroid_hz` is constant for N chunks | `spectral_trend` = 0.0; timbre descriptor omitted or neutral |
| Very high BPM (>220) or very low (<30) | `delta_bpm` computed normally; no artificial clamping |
| `onset_regularity` autocorrelation has no clear peak | Returns 0.0 rather than raising; prompt omits onset regularity descriptor |
| HPSS produces zero total energy | `harmonic_ratio` = 0.5 (neutral default) or 0.0; no divide-by-zero exception |

---

## Out of Scope

- NOT: Layer 3 structural signals (self-similarity matrix, novelty detection, phrase length estimation, energy arc position, harmonic tension, repetition/novelty scores). These are Horizon 2.
- NOT: Layer 4 interaction alpha signals (engagement prediction, intent classification, fatigue detection, session arc model). These are Horizon 3.
- NOT: Any new ML model training, inference, or loading. All Horizon 1 computation is librosa functions and NumPy arithmetic.
- NOT: Session logging infrastructure. Storing full (features, generation, timestamp) tuples for offline training is Horizon 2 pre-work.
- NOT: UI restructuring beyond adding trend indicators to the existing dashboard. No new pages, no new layout.
- NOT: Extending the history ring beyond 30 entries. The current ring capacity is a fixed architectural parameter for v1. Window size N must operate within it.
- NOT: CENS feature (`librosa.feature.chroma_cens`) unless OQ-01 latency analysis confirms it fits within budget without redundancy with existing chroma.
- NOT: `percussive_ratio` as a separate key — it is derivable as `1 - harmonic_ratio` if needed downstream.
- NOT: `mfcc_delta` / `mfcc_delta_delta` (13-dimensional delta arrays). These are COULD-add in a future Horizon 1 extension, not v1 of Horizon 1.
- NOT: `spectral_bollinger` — a COULD-add deferred until the value of band position tracking is validated in practice.
- NOT: Changing the WebSocket protocol, Redis schema, or store interface. All changes are additive.
- Deferred: Configurable history window per indicator type. A single global N is sufficient for Horizon 1.
- Deferred: Exporting Layer 2 indicators to the REST API. For Horizon 1, they feed the prompt builder and UI only.

---

## Constraints

- Must: End-to-end latency from audio chunk arrival to feature availability remains below 2 seconds. Layer 1 widening and Layer 2 computation combined must not add more than approximately 500ms to the existing extraction time.
- Must: All new code uses only libraries already in requirements.txt (librosa, numpy, scipy). No new production dependencies introduced.
- Must: The existing `FeatureVector` schema (13 keys) is additive-only extended. No existing key is renamed, removed, or changed in type.
- Must: The v1 `build_prompt()` function continues to work on the updated FeatureVector. It does not need to call Layer 2 indicators.
- Must: Layer 2 computation must not call into `extract_features()`. It reads from the history ring only.
- Must: All computation is open-source (MIT/Apache 2/ISC). No AGPL or proprietary code introduced.
- Must: The system remains runnable without Redis. The DictStore fallback must support Layer 2 via `get_history()` exactly as it does today.
- Must not: Raise unhandled exceptions on cold start (0 or <N history entries). All Layer 2 and prompt builder v2 paths must degrade gracefully.
- Must not: Block the FastAPI async event loop. Any compute-heavy Layer 2 operation must run in the existing background thread or be fast enough to be synchronous (< 50ms).
- Assumes: The existing history ring returns entries newest-first (confirmed in `dict_store.py`: `deque.appendleft`, `get_history` returns `list(self._history)[:limit]`).
- Assumes: The demo hardware (RTX 5090, 64GB RAM) has sufficient CPU headroom for librosa operations at the 2-second chunk cadence.
- Assumes: Layer 2 indicators are computed fresh each cycle from the history ring. They are not persisted to the store. (No store schema change.)

---

## Open Questions (Resolved)

All seven open questions were resolved by the Technical Director before architecture began. The history is preserved here for reference.

### OQ-01: Layer 1 widening latency budget

Which of the seven MUST-add Layer 1 features, if any, cause the combined `extract_features()` call to exceed 500ms on the demo hardware? Specifically: `tonnetz` and `harmonic_ratio` (which requires HPSS) are the most computationally expensive. Does HPSS fit within the budget at 2-second chunks, or should it be measured first and conditionally included?

**RESOLVED — benchmark-first as Slice 1 (H1.S01). All 7 Layer 1 features remain MUST. If the benchmark shows `harmonic_ratio` or `tonnetz` exceeds budget, downgrade is a documented amendment path requiring a spec update.**

### OQ-02: Which Layer 2 SHOULD indicators are in v1 of Horizon 1?

The SHOULD list contains 9 additional indicators (`bpm_ma`, `energy_volatility`, `key_change_rate`, `spectral_bollinger`, `onset_density`, `mfcc_delta`, `harmonic_percussive_ratio` trend, `flux_trend`, `dynamic_range`). Are any of these required for the v2 prompt builder to be meaningfully richer than v1? Or are the 9 MUST indicators sufficient for Horizon 1's first forge sprint?

**RESOLVED — 9 MUST indicators only. No SHOULD promotions. The MUST set is sufficient for the v2 prompt builder use cases in Horizon 1.**

### OQ-03: Trajectory descriptor thresholds

FR-03a through FR-03h specify threshold conditions (e.g., "positive beyond a threshold"). These thresholds are not defined in any existing spec. Examples: at what `delta_bpm` value does "accelerating" become meaningful? At what `key_stability` fraction is the key "stable"? At what `spectral_trend` magnitude is timbre "brightening"?

**RESOLVED — thresholds are defined as named constants in `src/features/thresholds.py`. Not env vars. Initial values set by the architect; tunable during play-testing (H1.S08).**

### OQ-04: Window size N for Layer 2 computation

The history ring holds 30 entries. What window size N should be used for temporal indicators? The specs do not specify a default. Options range from 5 (responsive, noisy) to 30 (smooth, sluggish). Different indicators may benefit from different N values (e.g., `key_stability` over 8 chunks vs `energy_momentum` over 5).

**RESOLVED — global N=10 via `HORIZON1_WINDOW_N` environment variable (default 10). Per-indicator window sizes are out of scope for Horizon 1.**

### OQ-05: Where does Layer 2 computation live in the call stack?

The specs identify three candidate integration points: (a) inside `extract_features()` — reads its own output + history, computes Layer 2 inline; (b) a new `compute_indicators(history)` function called by the GenerationEngine before building the prompt; (c) a new `compute_indicators(history)` function called inside `build_prompt_v2()` itself.

Option (a) requires `extract_features()` to have store access, which it does not currently have. Options (b) and (c) are more modular but require the caller to wire history.

**RESOLVED — `compute_indicators()` lives in `src/features/indicators.py` and is called by the caller that owns the history (i.e., the mic loop / GenerationEngine wiring layer). `extract_features()` stays Layer-1-pure with no store access.**

### OQ-06: Are Layer 2 indicators added to the FeatureVector or kept separate?

Layer 2 indicators could be: (a) added as new keys to the FeatureVector dict and persisted to the store alongside Layer 1 data; (b) returned as a separate dict and never persisted; (c) embedded in an extended payload used only for prompt building and UI updates.

FR-02 currently states "computed on each cycle" and the Constraints section states "not persisted to the store." However, option (a) would allow the WebSocket to stream Layer 2 data to the UI without additional plumbing. Option (b) keeps the store schema clean.

**RESOLVED — Layer 2 indicators are derived, not persisted. Store schema is unchanged. The WebSocket payload is extended to carry both layers (Layer 1 FeatureVector + Layer 2 indicators dict) in a single broadcast frame.**

### OQ-07: Does Horizon 1 include UI work?

specs/04-HORIZONS.md lists "UI trend indicators (spark lines, direction arrows)" as one of 4 slices in Horizon 1. US-04 and AC-10 assume this is in scope. However, the task brief says "UI restructuring beyond trend indicators is out of scope." The boundary is ambiguous: are spark lines a "trend indicator" (in scope) or "UI restructuring" (out of scope)?

**RESOLVED — UI scope is 4 additive elements: 2 sparklines (BPM, energy), 1 spectral direction arrow, 1 energy regime pill. No layout restructuring. These are added to the existing dashboard without modifying the current element positions or page structure.**

---

*Document by: @requirements-analyst*
*v1.1 edits: G-07 MFCC coefficient text corrected; OQ-01..OQ-07 marked RESOLVED per TD decisions.*
*Inputs: specs/04-HORIZONS.md, specs/05-SONIC-ALPHA.md, specs/02-ARCHITECTURE.md, specs/00-DECISIONS.md, src/features/engine.py, src/generation/prompt.py, src/store/dict_store.py + base.py*
