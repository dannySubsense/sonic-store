# Horizon 1 — Implementation Roadmap: Derivative Features
**Version:** 1.1
**Date:** 2026-04-16
**Status:** READY FOR IMPLEMENTATION
**Author:** @planner

---

## 0. How to Read This Document

Slices are numbered H1.S01 through H1.S08 and ordered by dependency. Each slice must be fully complete — all tests passing — before the next dependent slice begins. No partial work. No skipping ahead.

The benchmark (H1.S01) is the gate for all feature work. If HPSS breaches the 500ms budget, an explicit amendment path is defined before any Layer 1 code is written.

**Total Horizon 1 slices:** 8
**Complexity tags:** XS / S / M / L (not calendar hours — relative implementation weight)

---

## 1. Scope Recap

Horizon 1 widens Layer 1 by adding seven new acoustic features to `extract_features()` (all available in librosa with no new dependencies), introduces Layer 2 by computing nine temporal indicators from the 30-entry history ring, replaces the v1 prompt builder call inside `GenerationEngine` with a new `build_prompt_v2()` that incorporates trajectory descriptors derived from those indicators, extends the WebSocket broadcast payload to carry both Layer 1 features and Layer 2 indicators, and updates `ui/app.js` to display four new visual elements (BPM sparkline, energy sparkline, spectral direction arrow, energy regime pill). The v1 `build_prompt()` function remains callable unchanged. Store schema, REST endpoints, and store interface are untouched. All open questions from `01-REQUIREMENTS.md` have been resolved by TD decisions in `02-ARCHITECTURE.md`. No new ML models, no new production dependencies, no Layer 3 or Layer 4 signals are in scope.

---

## 2. Dependency Map

```
H1.S01 Latency Benchmark
    │
    ▼  (confirms Layer 1 MUST list or triggers amendment)
H1.S02 Layer 1 Widening
    │
    ├──────────────────────────────┐
    ▼                              │ (can start in parallel once S02 is defined)
H1.S03 Layer 2 Indicators     H1.S02 also defines thresholds module
    │                              │
    ▼                              ▼
H1.S04 Prompt Builder v2      H1.S02 (thresholds.py available; S04 imports it)
    │
    ▼
H1.S05 GenerationEngine Wiring
    │
    ▼
H1.S06 WebSocket Payload Extension
    │
    ▼
H1.S07 Web UI — Indicator Elements
    │
    ▼
H1.S08 Polish + Integration Verification
```

Ordered blocking chain:
- H1.S01 blocks H1.S02 (benchmark verdict determines MUST list)
- H1.S02 blocks H1.S03 (history ring now contains Layer 1 extended vectors; `thresholds.py` is needed by S03)
- H1.S03 blocks H1.S04 (prompt builder v2 reads indicator output)
- H1.S04 blocks H1.S05 (GenerationEngine imports `build_prompt_v2`)
- H1.S05 blocks H1.S06 (WS payload extension depends on indicators being computed in the engine; conceptually decoupled but shares `app.py`)
- H1.S06 blocks H1.S07 (UI consumes the extended WS payload shape)
- H1.S07 blocks H1.S08 (polish requires all elements to exist)

---

## 3. Slice Detail

---

### H1.S01: Latency Benchmark

**Goal:** Measure the wall-clock cost of each new Layer 1 feature extraction call on the demo hardware (RTX 5090, 64GB RAM) and produce a numbered, persisted benchmark report before any Layer 1 code enters the codebase.

**Complexity:** S

**Files Touched:**

| File | Action |
|------|--------|
| `benchmarks/horizon-1-layer-1-latency.md` | CREATE — benchmark report artifact |
| `scripts/benchmark_layer1.py` | CREATE — benchmark runner script |

No production source files are modified in this slice.

**Preconditions:**

- v1 codebase complete (S01–S11 DONE per CLAUDE.md)
- Demo hardware (RTX 5090) available and running
- All v1 tests passing (`make test` exits 0)
- `tests/fixtures/440hz_sine_2s.wav`, `tests/fixtures/silence_2s.wav`, and `tests/fixtures/chirp_2s.wav` exist

**Work Items:**

- Create `scripts/benchmark_layer1.py` that:
  - Loads each of the three test fixtures as numpy arrays (same `librosa.load` call used in `test_features.py`)
  - For each new Layer 1 feature, times its computation in isolation using `time.perf_counter()` over 10 warm-up runs then 30 timed runs; reports mean and p95
  - Features to time individually: `spectral_rolloff_hz`, `spectral_flux`, `spectral_contrast`, `zero_crossing_rate`, `mfcc`, `harmonic_ratio` (HPSS), `tonnetz`
  - Times the full proposed `extract_features()` call (v1 baseline + all 7 new features together) over 30 runs
  - Prints a markdown table: feature name, mean ms, p95 ms, pass/fail vs. the per-feature budget implied by the 500ms total ceiling
  - Writes the same table to `benchmarks/horizon-1-layer-1-latency.md` with a top-level verdict line: "PASS — all 7 MUST features fit within 500ms budget" or "FAIL — see amendment path below"
- Create `benchmarks/` directory (with a `.gitkeep` if needed)
- Run `scripts/benchmark_layer1.py` on the demo hardware and commit the resulting `benchmarks/horizon-1-layer-1-latency.md`
- If `harmonic_ratio` (HPSS) or `tonnetz` individually exceeds 300ms mean on the demo hardware, the report must include the amendment path section (see below)
- For `spectral_flux`, compute the raw (pre-normalization) value for each fixture: `np.sum(np.diff(np.abs(librosa.stft(audio)), axis=1) ** 2, axis=0).mean()`. Print per-fixture raw flux and its p95 across all 30 timed runs. Include these raw flux statistics in the `benchmarks/horizon-1-layer-1-latency.md` report in a dedicated 'Raw Spectral Flux Calibration' section.
- Recommend a `FLUX_NORM_DIVISOR` value in the benchmark report based on the fixtures' raw flux p95. Rule: set `FLUX_NORM_DIVISOR` to roughly the p95 of raw flux across music-like fixtures (chirp, sine) so that typical music flux maps to ~[0.3, 0.95] and silence maps to ~0. Explicitly document the recommended numeric value in the report.

**Amendment Path (if benchmark FAILS):**

If the benchmark report shows that `harmonic_ratio` (HPSS) causes the combined `extract_features()` call to exceed 500ms:
- Document the finding in `benchmarks/horizon-1-layer-1-latency.md`
- Downgrade `harmonic_ratio` from MUST to SHOULD in the Horizon 1 MUST list
- If `harmonic_ratio` is removed, `tonnetz` falls back to full audio (already architected; no code change needed for the fallback — it is the default path when HPSS energy < threshold)
- Note in the benchmark report: "H1.S02 proceeds with 6 MUST features; harmonic_ratio may be re-introduced post-Horizon 1 if HPSS is optimized via single-STFT reuse"
- No architecture doc change is required — `02-ARCHITECTURE.md` Section 3.2 already documents this path

**Tests:**

- No pytest tests for this slice (benchmark script is not a unit test)
- Done criteria are human-reviewed artifacts (the benchmark report file)
- The script itself should exit non-zero if any feature call raises an exception

**Acceptance:**

- Closes AC-02 (Layer 1 extraction latency measurement — this slice produces the measurement that proves or disproves the 500ms budget)
- Prerequisite for AC-01 (the MUST list is confirmed before implementation begins)

**Rollback Plan:** Yes — this slice creates only `scripts/benchmark_layer1.py` and `benchmarks/horizon-1-layer-1-latency.md`. Reverting the commit removes both files and leaves the codebase exactly as before.

---

### H1.S02: Layer 1 Widening + Thresholds Module

**Goal:** Add all seven MUST Layer 1 features to `extract_features()` and create the `thresholds.py` constants module; all new and existing feature tests pass.

**Complexity:** M

**Files Touched:**

| File | Action |
|------|--------|
| `src/features/engine.py` | MODIFY — add seven new Layer 1 keys to `extract_features()` return dict |
| `src/features/thresholds.py` | CREATE — named threshold constants used by Layer 2 and prompt builder v2 |
| `tests/test_features.py` | MODIFY — add assertions for all seven new Layer 1 keys |

**Preconditions:**

- H1.S01 complete: `benchmarks/horizon-1-layer-1-latency.md` exists with a PASS verdict
- H1.S01 complete AND benchmark report contains a recommended `FLUX_NORM_DIVISOR` value. Before writing Layer 1 feature tests in this slice, update `src/features/thresholds.py`'s `FLUX_NORM_DIVISOR` from the placeholder `1.0` to the recommended value from the benchmark report. If the benchmark report's recommended value is not present, HALT H1.S02 and return to H1.S01.
- If benchmark produced an amendment (HPSS removed from MUST): implement only the 6 remaining MUST features in this slice; mark `harmonic_ratio` as deferred in a code comment
- All v1 tests still passing

**Work Items:**

- Create `src/features/thresholds.py` with all named constants as specified in `02-ARCHITECTURE.md` Section 5:
  - `DELTA_BPM_THRESHOLD = 2.0`
  - `KEY_STABLE_HIGH = 0.75`
  - `KEY_STABLE_LOW = 0.40`
  - `ENERGY_MOMENTUM_RISING_THRESHOLD = 0.01`
  - `ENERGY_MOMENTUM_FALLING_THRESHOLD = -0.01`
  - `SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50.0`
  - `SPECTRAL_TREND_DARKENING_THRESHOLD = -50.0`
  - `FLUX_NORM_DIVISOR = <benchmark-derived p95 from H1.S01 report>` (must be set before `test_spectral_flux_range` is committed; placeholder value removed in this slice)
- Modify `src/features/engine.py` to add the seven new Layer 1 computation blocks as specified in `02-ARCHITECTURE.md` Section 3.2:
  - `spectral_rolloff_hz`: `librosa.feature.spectral_rolloff(..., roll_percent=0.85).mean()`
  - `spectral_flux`: STFT magnitude diff-squared, normalized by `FLUX_NORM_DIVISOR` from `thresholds.py`, clipped to `[0, 1]`
  - `spectral_contrast`: `librosa.feature.spectral_contrast(..., n_bands=6).mean(axis=1).tolist()` (length 7)
  - `zero_crossing_rate`: `librosa.feature.zero_crossing_rate(...).mean()` divided by `0.3`, clipped to `[0, 1]`
  - `mfcc`: `librosa.feature.mfcc(..., n_mfcc=13).mean(axis=1).tolist()` (length 13)
  - `harmonic_ratio`: `librosa.effects.hpss(audio)` → energy ratio with `1e-8` guard returning `0.5` for silence
  - `tonnetz`: `librosa.feature.tonnetz(y=harmonic_component, sr=sr).mean(axis=1).tolist()` (length 6) with NaN/Inf guard returning `[0.0]*6`
  - Reuse the `harmonic` component from HPSS as input to `tonnetz` (code-reuse optimization from Section 3.3; share the HPSS decomposition)
- Add NaN/Inf guards per `02-ARCHITECTURE.md` Section 3.4
- All 13 existing keys must remain present and unchanged in type/shape after the modification
- Modify `tests/test_features.py` to add the following test cases:
  - `test_layer1_new_keys_present`: Given a sine fixture, assert all 7 new keys are in the returned dict
  - `test_spectral_rolloff_hz_range`: float, > 0.0 and <= 11025.0
  - `test_spectral_flux_range`: float in `[0.0, 1.0]`
  - `test_spectral_contrast_shape`: list of 7 floats
  - `test_spectral_contrast_finite`: asserts all values in the `spectral_contrast` list are finite floats (no NaN/Inf) across silent, sine, and noise fixtures; closes OQ-PLAN-02
  - `test_zero_crossing_rate_range`: float in `[0.0, 1.0]`
  - `test_mfcc_shape`: list of 13 floats
  - `test_harmonic_ratio_range`: float in `[0.0, 1.0]`
  - `test_tonnetz_shape`: list of 6 floats
  - `test_silence_sentinel_values`: Given zero array, assert `harmonic_ratio == 0.5`, `tonnetz == [0.0]*6`, `spectral_flux == 0.0`, no exception
  - `test_impulse_no_nan_inf`: Given single-spike array, assert all 7 new values are finite (no NaN, no Inf)
  - `test_v1_keys_preserved`: Assert all 13 v1 keys remain present after Layer 1 widening

**Tests:**

- `tests/test_features.py` — new test cases listed above (12 new test functions)
- Run command: `pytest tests/test_features.py -v`
- All new tests plus all pre-existing tests in the file must pass

**Acceptance:**

- Closes AC-01 (all seven new Layer 1 keys present with correct type/shape/range)
- Closes AC-02 (latency confirmed by H1.S01; this slice inherits the pass)
- Contributes to AC-09 (v1 keys preserved)
- FR-01 MUST features all implemented

**Rollback Plan:** Yes — reverts to v1 `engine.py` and removes `thresholds.py`. All v1 tests continue to pass.

---

### H1.S03: Layer 2 Indicators Module

**Goal:** Create `src/features/indicators.py` with `compute_indicators(history, window)` returning all nine MUST temporal indicators; cold-start, edge cases, and all indicator computation tests pass.

**Complexity:** M

**Files Touched:**

| File | Action |
|------|--------|
| `src/features/indicators.py` | CREATE — Layer 2 computation module |
| `tests/test_indicators.py` | CREATE — unit tests for all nine indicators |

**Preconditions:**

- H1.S02 complete: `src/features/thresholds.py` exists (indicators module imports from it)
- H1.S02 complete: history ring now stores 20-key FeatureVectors (Layer 1 widened); the history snapshots passed to `compute_indicators` contain the richer vectors, though Layer 2 only reads the Layer 1 original fields (`bpm`, `rms_energy`, `chroma`, `key_pitch_class`, `key_mode`, `spectral_centroid_hz`, `onset_strength`) — no dependency on the new Layer 1 fields

**Work Items:**

- Create `src/features/indicators.py` implementing `compute_indicators(history, window)` exactly as specified in `02-ARCHITECTURE.md` Sections 4.1–4.5:
  - Module constant: `HORIZON1_WINDOW_N: int = int(os.getenv("HORIZON1_WINDOW_N", "10"))`
  - `_cold_start_result()` helper returning dict with `available=False` and all indicators as `None`
  - Window clamping: `min(window, 30, len(history))`; return cold-start if `len(history) < HORIZON1_WINDOW_N`
  - Time-ordered window: `ordered = list(reversed(history[:window]))` (oldest-first)
  - `_regression_delta(series)` — Davis & Mermelstein weighted regression derivative helper
  - `delta_bpm`: `_regression_delta(bpm_series)` — positive = accelerating
  - `bpm_volatility`: `np.std(bpm_series)` — no divide-by-zero possible
  - `energy_momentum`: `np.polyfit(x, energy_series, 1)[0]` — linear regression slope
  - `energy_regime`: threshold classification using `ENERGY_MOMENTUM_RISING_THRESHOLD` / `ENERGY_MOMENTUM_FALLING_THRESHOLD` from `thresholds.py`
  - `chroma_entropy`: Shannon entropy on `history[0]["chroma"]` (current chunk only, not window); `0.0` guard for near-zero chroma sum
  - `chroma_volatility`: `np.std(chroma_matrix, axis=0).mean()` over window entries
  - `key_stability`: most-common-key fraction over window using `(key_pitch_class, key_mode)` tuples
  - `spectral_trend`: `_regression_delta(centroid_series)` — same formula as `delta_bpm`
  - `onset_regularity`: normalized autocorrelation peak at non-zero lag; `0.0` for constant series; clipped to `[0.0, 1.0]`
  - Function is a pure function (no shared state mutations); thread-safe by design
- Create `tests/test_indicators.py` with the following test cases:
  - `test_cold_start_empty_history`: `compute_indicators([], window=10)` returns `{"available": False, ...all None}`, no exception
  - `test_cold_start_one_entry`: single-entry history returns cold-start
  - `test_cold_start_n_minus_one`: exactly `N-1` entries returns cold-start
  - `test_warm_exactly_n_entries`: exactly N entries returns `{"available": True}` with all float/str values (no None)
  - `test_delta_bpm_positive`: 10 entries with monotonically increasing BPM → `delta_bpm > 0`
  - `test_delta_bpm_zero_constant_bpm`: 10 identical BPM entries → `delta_bpm == 0.0` and `bpm_volatility == 0.0`
  - `test_energy_momentum_rising`: 10 entries with monotonically increasing `rms_energy` → `energy_momentum > 0` and `energy_regime == "rising"`
  - `test_energy_momentum_stable`: 10 entries with constant `rms_energy` → `energy_regime == "stable"`
  - `test_chroma_volatility_zero`: 10 entries with identical chroma vectors → `chroma_volatility == 0.0`
  - `test_chroma_entropy_uniform`: uniform chroma (all equal) → `chroma_entropy` close to `log(12)` (max entropy)
  - `test_key_stability_full`: 10 entries all same key → `key_stability == 1.0`
  - `test_key_stability_all_different`: 10 entries each a different key → `key_stability == pytest.approx(1.0/10)`
  - `test_spectral_trend_positive`: 10 entries with increasing `spectral_centroid_hz` → `spectral_trend > 0`
  - `test_onset_regularity_constant_signal`: constant `onset_strength` series → `onset_regularity == 0.0`
  - `test_window_clamp_beyond_30`: set `HORIZON1_WINDOW_N` env to "50" → function clamps window to 30 without exception (monkeypatch)
  - `test_latency_under_50ms`: compute_indicators on 30-entry fixture → assert wall-clock time < 50ms (AC-05)

**Tests:**

- `tests/test_indicators.py` — 16 new test functions
- Run command: `pytest tests/test_indicators.py -v`

**Acceptance:**

- Closes AC-03 (all nine MUST indicators computed, correct types and ranges)
- Closes AC-04 (cold-start behavior: 0, 1, N-1, and N entries all handled correctly)
- Closes AC-05 (Layer 2 latency < 50ms verified by `test_latency_under_50ms`)
- FR-02 MUST indicators fully implemented

**Rollback Plan:** Yes — remove `src/features/indicators.py` and `tests/test_indicators.py`. No existing files are modified; codebase reverts cleanly.

---

### H1.S04: Prompt Builder v2

**Goal:** Create `src/generation/prompt_v2.py` with `build_prompt_v2(features, indicators)` that incorporates trajectory descriptors when indicators are available and falls back to `build_prompt()` on cold-start; snapshot and trajectory descriptor tests pass.

**Complexity:** M

**Files Touched:**

| File | Action |
|------|--------|
| `src/generation/prompt_v2.py` | CREATE — prompt builder v2 |
| `tests/test_prompt_v2.py` | CREATE — unit tests for v2 including cold-start fallback, descriptor presence, output invariants, and snapshot |

**Preconditions:**

- H1.S03 complete: `src/features/indicators.py` exists (the test fixtures for `test_prompt_v2.py` construct indicator dicts directly; no live `compute_indicators` call needed)
- H1.S02 complete: `src/features/thresholds.py` exists (prompt_v2 imports threshold constants from it)
- v1 `src/generation/prompt.py` unchanged and tested

**Work Items:**

- Create `src/generation/prompt_v2.py`:
  - Import `build_prompt` from `src/generation/prompt` and re-export it for backward compatibility
  - Import threshold constants from `src/features/thresholds.py`
  - Inline-duplicate `_KEY_NAMES` and the three descriptor helpers (`_tempo_descriptor`, `_energy_descriptor`, `_timbre_descriptor`) from `src/generation/prompt.py` into `src/generation/prompt_v2.py` as local private helpers; do not import the underscore-prefixed names from `prompt.py` (they are module-private and importing them would couple the module to an internal implementation detail)
  - Implement `build_prompt_v2(features: dict, indicators: dict | None) -> str` as specified in `02-ARCHITECTURE.md` Sections 6.1–6.6:
    - Cold-start gate: `if indicators is None or not indicators.get("available", False): return build_prompt(features)`
    - Trajectory phrase assembly in order: energy → tempo → key → timbre (per Section 6.4 condition table)
    - Output template from Section 6.5: with trajectory if phrases present, without if empty (exact v1 format)
    - Output invariants: non-empty str, no `\n`, no JSON/brackets/special tokens (Section 6.6)
- Create `tests/test_prompt_v2.py` with the following test cases:
  - `test_cold_start_none_indicators`: `build_prompt_v2(features, None)` returns same string as `build_prompt(features)` (exact string match)
  - `test_cold_start_unavailable_indicators`: `build_prompt_v2(features, {"available": False, ...all None})` returns same string as `build_prompt(features)`
  - `test_no_exception_zero_history`: `build_prompt_v2(valid_features, None)` — no exception
  - `test_rising_energy_regime_descriptor`: `energy_regime="rising"` → output contains at least one of: "building", "increasing", "rising"
  - `test_falling_energy_regime_descriptor`: `energy_regime="falling"` → output contains at least one of: "fading", "diminishing", "decreasing"
  - `test_accelerating_bpm_descriptor`: `delta_bpm > DELTA_BPM_THRESHOLD` → output contains at least one of: "accelerating", "pushing tempo", "quickening"
  - `test_decelerating_bpm_descriptor`: `delta_bpm < -DELTA_BPM_THRESHOLD` → output contains at least one of: "decelerating", "pulling back", "slowing"
  - `test_key_stability_high_descriptor`: `key_stability > KEY_STABLE_HIGH` → output contains "harmonically stable"
  - `test_spectral_trend_brightening_descriptor`: `spectral_trend > SPECTRAL_TREND_BRIGHTENING_THRESHOLD` → output contains "bright"
  - `test_output_is_nonempty_string`: given any valid indicators dict, output is non-empty `str`
  - `test_output_no_newlines_or_json`: assert `"\n" not in output` and `"{" not in output` and `"[" not in output`
  - `test_snapshot_full_trajectory`: fixture history (rising energy, same key, accelerating BPM, brightening spectral) → assert prompt string equals a documented expected snapshot string; this is the regression guard. TDD note: stub `expected=""` initially, implement `build_prompt_v2`, run to capture actual output, assert stability, then commit the captured snapshot (capture-after-impl workflow — closes OQ-PLAN-04).
  - `test_v1_prompt_callable_on_new_featurevector`: `build_prompt(20_key_feature_vector)` returns valid string without error (AC-09 v1 backward compat)

**Tests:**

- `tests/test_prompt_v2.py` — 13 new test functions
- Run command: `pytest tests/test_prompt_v2.py -v`
- Also run `pytest tests/test_prompt.py -v` to confirm v1 prompt builder is unaffected

**Acceptance:**

- Closes AC-06 (trajectory descriptors present for each condition)
- Closes AC-07 (cold-start fallback matches v1 format exactly)
- Closes AC-08 (output is valid MusicGen input: non-empty str, natural language only)
- Closes AC-09 (v1 `build_prompt()` callable on updated FeatureVector)
- FR-03a through FR-03j all covered

**Rollback Plan:** Yes — remove `src/generation/prompt_v2.py` and `tests/test_prompt_v2.py`. No existing files modified. `GenerationEngine` not yet wired to v2 at this slice.

---

### H1.S05: GenerationEngine Wiring

**Goal:** Update `src/generation/engine.py` to call `compute_indicators()` then `build_prompt_v2()` in the generation loop; integration test with a populated DictStore fixture confirms trajectory descriptors appear in the generated clip's prompt.

**Complexity:** S

**Files Touched:**

| File | Action |
|------|--------|
| `src/generation/engine.py` | MODIFY — update generation loop to call `get_history`, `compute_indicators`, `build_prompt_v2` |
| `tests/test_generation.py` | MODIFY — add two new test cases for v2 prompt wiring |

**Preconditions:**

- H1.S04 complete: `src/generation/prompt_v2.py` exists and is tested
- H1.S03 complete: `src/features/indicators.py` exists
- All existing `tests/test_generation.py` tests pass

**Work Items:**

- Modify `src/generation/engine.py` generation loop per `02-ARCHITECTURE.md` Section 6.7:
  - Replace `from src.generation.prompt import build_prompt` import with `from src.generation.prompt_v2 import build_prompt_v2`
  - Add import: `from src.features.indicators import compute_indicators, HORIZON1_WINDOW_N`
  - In `_loop()`, after `features = store.get_latest()` and timestamp dedup check, add:
    ```
    history = self._store.get_history(HORIZON1_WINDOW_N)
    indicators = compute_indicators(history, window=HORIZON1_WINDOW_N)
    prompt = build_prompt_v2(features, indicators)
    ```
  - Remove the old `prompt = build_prompt(features)` call
  - All other loop logic unchanged (dedup, clip generation, queue output)
- Add to `tests/test_generation.py`:
  - `test_generation_v2_prompt_with_history`: Given a DictStore populated with 10 FeatureVector entries (fixture with rising energy, same key), mock `MusicGen.generate()`, start `GenerationEngine`, assert `output_queue.get()` produces a `GeneratedClip` whose `.prompt` contains at least one trajectory descriptor (e.g., "building" or "rising")
  - `test_generation_v2_cold_start_prompt`: Given a DictStore with 0 entries, assert `GeneratedClip.prompt` matches v1 format (contains "instrumental", contains key name, no trajectory phrases) — cold-start fallback path
- All 6 existing generation tests must still pass

**Tests:**

- `tests/test_generation.py` — 2 new test functions added to existing file
- Run command: `pytest tests/test_generation.py -v`

**Acceptance:**

- Closes the generation-side requirement of AC-06 (trajectory descriptors reach the generated clip prompt)
- Contributes to AC-07 (cold-start fallback in generation path)
- FR-03 fully wired into the production generation loop

**Rollback Plan:** Yes — revert `engine.py` to re-import `build_prompt` and remove the two new test cases. The v2 module remains but is unused.

---

### H1.S06: WebSocket Payload Extension

**Goal:** Extend the `mic_loop` broadcast in `src/api/app.py` to compute and include Layer 2 indicators in every WebSocket frame as `{"type": "features", "data": fv, "indicators": ind_or_null}`; existing WS tests pass; new WS payload shape test passes.

**Complexity:** S

**Files Touched:**

| File | Action |
|------|--------|
| `src/api/app.py` | MODIFY — `mic_loop` broadcast + `demo_start` endpoint to compute indicators and include in WS frame |
| `tests/test_api.py` | MODIFY — add three new tests for WS payload shape with indicators field |

**Preconditions:**

- H1.S03 complete: `src/features/indicators.py` exists
- H1.S05 complete (the generation loop already uses indicators; the WS path is a second call site, but the module is available)
- All existing `tests/test_api.py` tests pass

**Work Items:**

- Modify `src/api/app.py` in the `mic_loop` function per `02-ARCHITECTURE.md` Section 7.4:
  - Add imports: `from src.features.indicators import compute_indicators, HORIZON1_WINDOW_N`
  - After `store.write(features)`, call:
    ```python
    history = store.get_history(HORIZON1_WINDOW_N)
    indicators = compute_indicators(history, window=HORIZON1_WINDOW_N)
    ind_payload = indicators if indicators.get("available") else None
    ```
  - Change broadcast call from `{"type": "features", "data": features}` to `{"type": "features", "data": features, "indicators": ind_payload}`
- Modify the `demo/start` endpoint to iterate ALL chunks per file (replacing `first_chunk = next(chunks)`). For each WAV file: iterate the generator returned by `load_and_chunk(str(wav_path))`; for each chunk call `extract_features(chunk, source="file")`, `store.write(features)`, the three-line indicator computation pattern (`history = store.get_history(HORIZON1_WINDOW_N); indicators = compute_indicators(history, window=HORIZON1_WINDOW_N); ind_payload = indicators if indicators.get("available") else None`), and `await manager.broadcast({"type": "features", "data": features, "indicators": ind_payload})`. Sleep `await asyncio.sleep(0.1)` between chunks within a file (chunk-level pacing) and `await asyncio.sleep(0.5)` between files (file-level pacing). Add a `chunks_processed` integer field to each per-file result entry in the response body. This is a critical demo surface — without full chunk iteration, history never reaches N=10 and Layer 2 indicators never populate in demo mode.
- Confirm that `src/api/websocket.py` `ConnectionManager.broadcast()` is payload-agnostic (it serializes whatever dict is passed); no change needed there
- Add to `tests/test_api.py`:
  - `test_ws_payload_includes_indicators_field`: Use the existing test broadcast helper or a mini fixture; send a features broadcast and assert the received JSON has an `"indicators"` key (may be `null` for cold-start DictStore)
  - `test_demo_start_broadcast_includes_indicators_field`: Assert that the sequence of broadcast frames emitted by the `POST /demo/start` endpoint contains the `"indicators"` field throughout. Capture the full frame sequence and verify: (i) broadcast frames emitted early in the request (history < N) carry `indicators: null`, AND (ii) broadcast frames emitted late in the request (history >= N) carry a populated indicators dict. The test must assert both sides of this null→populated transition, exercising the cold-start wire form and the populated wire form. This satisfies AC-04, AC-05, and a critical portion of AC-10 for demo mode.
  - `test_demo_start_response_includes_chunks_processed`: Assert the response body's `results` array contains `chunks_processed` as an integer per file entry. If the file is the standard 10-second demo fixture at 2-second chunks, `chunks_processed` should be 5.
- All pre-existing WebSocket tests must continue to pass

**Tests:**

- `tests/test_api.py` — 3 new test functions
- Run command: `pytest tests/test_api.py -v`

**Acceptance:**

- Closes the server-side requirement of AC-10 (indicators reach the UI via WS)
- Satisfies AC-09 (existing WS consumers that ignore the `indicators` field are unaffected — JSON additivity)
- FR-05 (Layer 2 availability signaling via `null` vs populated indicators)

**Rollback Plan:** Yes — revert `app.py` to the v1 broadcast call. WS frame reverts to 13-key (or now 20-key from S02) `data` field only. No test regressions if the new tests are also reverted.

---

### H1.S07: Web UI — Indicator Elements

**Goal:** Add four new visual elements to `ui/app.js` and `ui/index.html` (BPM sparkline, energy sparkline, spectral direction arrow, energy regime pill); all warm-up and live-data states render correctly as specified in `03-UI-SPEC.md`.

**Complexity:** M

**Files Touched:**

| File | Action |
|------|--------|
| `ui/index.html` | MODIFY — add `<canvas>` for sparklines, `<span>` for arrow and pill in the correct `.feature-row` positions |
| `ui/app.js` | MODIFY — add client-side sparkline buffers, `updateIndicatorDisplay()` function, update `onmessage` handler |
| `ui/style.css` | MODIFY — add regime pill colors, arrow color rules, sparkline canvas sizing |

**Preconditions:**

- H1.S06 complete: WS payload shape includes `"indicators"` field (null or populated)
- The existing `ui/app.js` `handleFeatureMessage` function processes `msg.data`; this slice adds `updateIndicatorDisplay(msg.indicators)` alongside it

**Work Items:**

- Modify `ui/index.html`:
  - Add `<canvas id="sparkline-bpm">` inside the BPM `.feature-row`, to the right of `#val-bpm`
  - Add `<canvas id="sparkline-energy">` inside the Energy `.feature-row`, to the right of `#val-energy`
  - Add `<span id="regime-pill">warming up</span>` inside the Energy `.feature-row`, to the right of `#sparkline-energy`
  - Add `<span id="arrow-spectral" title="Warming up — need more history">—</span>` inside the Spectral `.feature-row`, to the right of `#val-spectral`
  - Verify flex layout can accommodate additions without overflow (per OQ-UI-01 guidance: sparkline canvas width 60–80px; can be reduced to ~40px if needed)
- Modify `ui/style.css`:
  - `#sparkline-bpm`, `#sparkline-energy`: inline canvas, height ~20px, width 70px (adjustable)
  - `#regime-pill`: rounded pill, monospace font; color rules for `rising` (muted green tint), `falling` (muted amber/red tint), `stable` (dark gray neutral); `transition: background-color 0.2s ease`
  - `#arrow-spectral`: same font-size as `.feature-value` (~16px); three color states (bright accent for `↑`, dimmed/cooler for `↓`, `#888` neutral gray for `→` and `—`)
- Modify `ui/app.js`:
  - Declare two rolling buffer arrays: `bpmBuffer = []` and `energyBuffer = []`, max length 10
  - Add `appendToSparklineBuffer(buffer, value, maxLen)` helper: pushes value, shifts off oldest if full
  - Add `drawSparkline(canvasId, buffer, yMin, yMax)` helper: clears canvas, draws polyline connecting data points left-to-right; blank right portion when fewer than 10 points
  - Add `updateIndicatorDisplay(indicators)` function:
    - If `indicators === null` or `indicators === undefined`: set `#arrow-spectral` to `—` with tooltip "Warming up — need more history"; set `#regime-pill` text to "warming up" with neutral style; return
    - Else: read `indicators.spectral_trend`, compare to ±50 thresholds (hardcoded per OQ-UI-02), set arrow symbol + color + tooltip accordingly; read `indicators.energy_regime`, set pill text + CSS class accordingly
  - Update `onmessage` handler (the function that dispatches WS messages):
    - After `updateFeatureDisplay(msg.data)` call (existing), add:
      - `appendToSparklineBuffer(bpmBuffer, msg.data.bpm, 10)`
      - `appendToSparklineBuffer(energyBuffer, msg.data.rms_energy, 10)`
      - `requestAnimationFrame(() => { drawSparkline("sparkline-bpm", bpmBuffer, 0, 250); drawSparkline("sparkline-energy", energyBuffer, 0, 1); })`
      - `updateIndicatorDisplay(msg.indicators)`
  - Handle error states: if `msg.data.bpm` is not a finite number, skip buffer append; if `indicators.spectral_trend` is null or non-finite, treat as cold-start
  - Confirm `#ai-prompt` has no overflow/height constraint that would truncate longer v2 prompt strings (per `03-UI-SPEC.md` Section 6 — no change expected; verify only)

**Tests:**

- No automated pytest tests for UI (matches v1 pattern from S07)
- Manual test checklist (must be checked before marking slice DONE):
  - [ ] Page loads at `http://localhost:8000/ui` with no console errors
  - [ ] All four new elements are visible in their warm-up / cold-start state on first load
  - [ ] After chunk 1–9: sparklines begin drawing partial lines; arrow shows `—`; pill shows `warming up`
  - [ ] After chunk 10: arrow transitions to directional symbol; pill transitions to colored regime label
  - [ ] Regime pill transitions between `rising` / `falling` / `stable` colors with 200ms CSS transition
  - [ ] Arrow tooltip renders on hover with correct text for each state
  - [ ] BPM sparkline scrolls left as new data arrives (oldest point drops off)
  - [ ] Energy sparkline y-axis correctly maps `rms_energy` 0.0–1.0 to canvas height
  - [ ] Energy row layout does not overflow the dashboard container at demo hardware resolution

**Acceptance:**

- Closes AC-10 (trend indicators visible for `energy_regime` and `delta_bpm`; "warming up" state shown when history < N)
- US-04 (trend indicators visible in UI)
- FR-05 (availability signaling via warm-up state)
- Closes all four new UI element requirements from `03-UI-SPEC.md` Sections 3.1–3.4

**Rollback Plan:** Yes — revert `index.html`, `app.js`, and `style.css` to prior state. Three-file revert; no backend changes to undo.

---

### H1.S08: Polish + Integration Verification

**Goal:** Run the full test suite, verify end-to-end behavior from mic input through indicators to UI display, confirm no v1 regressions, and close any open edge case gaps found during integration.

**Complexity:** S

**Files Touched:**

| File | Action |
|------|--------|
| `tests/test_features.py` | MODIFY — confirm all pre-Horizon-1 tests still pass; add any missed edge case tests |
| `tests/test_indicators.py` | MODIFY — add any edge cases discovered during H1.S07 integration |
| `tests/test_prompt_v2.py` | MODIFY — update snapshot test string if trajectory descriptor wording was adjusted |
| `src/features/thresholds.py` | MODIFY — update `FLUX_NORM_DIVISOR` if benchmark data suggests a better normalization divisor |
| `benchmarks/horizon-1-layer-1-latency.md` | MODIFY — append a "post-implementation verification" section with actual measured times after all code is in place |

**Preconditions:**

- H1.S01 through H1.S07 all complete and tests passing
- Manual UI test checklist from H1.S07 signed off

**Work Items:**

- Run `make test` (`pytest tests/ -v -m "not integration"`) and confirm all tests pass including all new Horizon 1 test files; zero failures, zero warnings about missing fixtures
- Run a full end-to-end manual session: start mic (or demo mode), observe sparklines growing, wait for chunk 10, confirm indicators light up, observe generated clip prompt in `#ai-prompt` — confirm trajectory phrases are present after warm-up
- Confirm `GET /features/latest` returns a 20-key FeatureVector (7 new keys visible in JSON response)
- Confirm `GET /features/history` returns 20-key FeatureVectors in the array
- Run `pytest tests/test_generation.py -v` to confirm generation engine integration (mocked) passes both old and new test cases
- If any edge case discovered during integration: add the test to the appropriate test file, fix the code, rerun `make test`
- Update `FLUX_NORM_DIVISOR` in `thresholds.py` if a better empirical value was found during play-testing (log the change and the reasoning in a comment)
- Append actual post-implementation timing data to `benchmarks/horizon-1-layer-1-latency.md`
- Confirm the v2 prompt snapshot test in `test_prompt_v2.py` matches the actual output (the snapshot was written in H1.S04; confirm it still holds after all wiring is done)
- Update CLAUDE.md implementation status table to reflect all H1.Sxx slices as DONE

**Tests:**

- Run command: `pytest tests/ -v -m "not integration"`
- All tests across all test files must pass
- Expected test count: 57 (v1 baseline) + ~34 new Horizon 1 tests = ~91 total

**Acceptance:**

- Closes AC-09 (existing consumers unaffected: REST endpoints return valid JSON, WS serializes correctly, v1 `build_prompt()` callable on 20-key FeatureVector)
- All requirement IDs from `01-REQUIREMENTS.md` have a corresponding slice and test (see mapping in Section 7 below)
- `make test` exits 0

**Rollback Plan:** This slice is purely additive test and verification work. If a bug is found and fixed, that fix is captured in the appropriate earlier slice's commit. The polish slice itself has no rollback concern.

---

## 4. Dependency Ordering — Rationale

| Position | Slice | Why Here |
|----------|-------|----------|
| 1 | H1.S01 Benchmark | TD decision: benchmark is the gate. No Layer 1 code before the latency verdict. |
| 2 | H1.S02 Layer 1 Widening | Cannot widen without the benchmark pass. `thresholds.py` is created here, unblocking S03 and S04. |
| 3 | H1.S03 Layer 2 Indicators | Must come after S02 because: (a) history ring now stores 20-key vectors (S03 reads from it); (b) `thresholds.py` exists. Does not need S04 or S05. |
| 4 | H1.S04 Prompt Builder v2 | Must come after S03 (imports indicator dict shape implicitly). Must come after S02 (imports `thresholds.py`). Isolated from GenerationEngine changes. |
| 5 | H1.S05 GenerationEngine Wiring | Must come after S04 (imports `build_prompt_v2`). Must come after S03 (imports `compute_indicators`). |
| 6 | H1.S06 WS Payload Extension | Must come after S03 (imports `compute_indicators`). Logically follows S05 so that `app.py` modifications are sequential (avoids merge conflicts). |
| 7 | H1.S07 Web UI | Must come after S06 (consumes extended WS payload shape). |
| 8 | H1.S08 Polish | Must come last: verifies everything integrates cleanly. |

---

## 5. Parallelizable Work

Two pairs of slices in this roadmap have no file overlap and can be worked in parallel by different people if the team grows:

**Pair A — Parallel after H1.S02 completes:**

| Parallel Slice | Files | No Conflict With |
|---------------|-------|-----------------|
| H1.S03 Layer 2 Indicators | `src/features/indicators.py`, `tests/test_indicators.py` | H1.S04 does not touch these files |
| H1.S04 Prompt Builder v2 | `src/generation/prompt_v2.py`, `tests/test_prompt_v2.py` | H1.S03 does not touch these files |

H1.S04 can begin as soon as the `thresholds.py` module exists (created in H1.S02) and the indicator dict return shape is documented (it is, in `02-ARCHITECTURE.md` Section 4.2). H1.S04's test fixtures construct indicator dicts manually — they do not call `compute_indicators`. So H1.S03 and H1.S04 can be built in parallel by two developers.

**Pair B — Parallel after H1.S05 completes:**

| Parallel Slice | Files | No Conflict With |
|---------------|-------|-----------------|
| H1.S06 WS Payload Extension | `src/api/app.py`, `tests/test_api.py` | H1.S07 does not touch Python backend |
| H1.S07 Web UI prep | `ui/index.html`, `ui/style.css` HTML/CSS groundwork | H1.S06 does not touch UI files |

A developer can add the HTML structure and CSS styles for the four new UI elements as soon as the WS payload shape is documented (it is, in `02-ARCHITECTURE.md` Section 7.2). The `app.js` wiring depends on H1.S06 being complete, but the HTML/CSS skeleton does not.

**Note for Danny (single developer):** The parallelization opportunities identify the natural breakpoints where context switching between backend and frontend work would be low-cost. The default is still sequential.

---

## 6. Risk + Mitigation Table

| Risk | Probability | Impact | Mitigating Slice | Mitigation |
|------|------------|--------|-----------------|------------|
| HPSS (`harmonic_ratio`) breaches 500ms budget on demo hardware | Low (RTX 5090 is fast CPU; HPSS is a median filter, not GPU-accelerated) | High (must remove a MUST feature) | H1.S01 | Benchmark runs before any Layer 1 code. Amendment path documented in S01 output. `tonnetz` falls back to full audio gracefully. `harmonic_ratio` can be re-introduced as SHOULD. |
| Cold-start behavior broken (Layer 2 raises on empty history) | Low (architecture explicitly covers this case) | Medium (UI shows broken state; generation may crash) | H1.S03, H1.S04 | `test_cold_start_empty_history` and `test_cold_start_one_entry` are required test cases. `build_prompt_v2` cold-start fallback test also covers this path end-to-end. |
| WS payload change breaks existing UI behavior | Low (JSON additivity; UI updated in same sprint) | High (demo UI broken) | H1.S06, H1.S07 | S06 is completed and tested before S07 begins. The `"indicators"` field is additive; the `"data"` field shape grows but old keys remain. WS tests verify JSON serialization. |
| v1 prompt builder regression | Very low (`prompt.py` not modified) | High (generation produces empty/malformed prompts) | H1.S04 | `test_v1_prompt_callable_on_new_featurevector` in `test_prompt_v2.py` asserts `build_prompt()` works on a 20-key FeatureVector. `pytest tests/test_prompt.py` runs unchanged. |
| `FLUX_NORM_DIVISOR` miscalibrated — `spectral_flux` becomes binary flag clipping all music to 1.0 | Low (now mitigated by explicit calibration gate in H1.S01 and H1.S02 precondition) | Medium (feature degraded to binary flag; not used in Horizon 1 prompt but corrupts the signal for future horizons) | H1.S01, H1.S02 | H1.S01 benchmark emits raw flux p95 and recommends `FLUX_NORM_DIVISOR`. H1.S02 precondition requires the benchmark-recommended value to be set before `test_spectral_flux_range` is committed. The test-ordering trap (divisor=1.0 makes range test trivially pass while real music clips) is closed. |
| Energy row flex layout overflows with 5 elements | Medium (depends on container width and rendered element sizes) | Low (cosmetic; dashboard still functions) | H1.S07 | UI spec acknowledges this in OQ-UI-03. Implementer should verify at demo hardware resolution. Sparkline canvas can shrink to ~40px. |
| `chroma_entropy` semantics mismatch (spec says "current chunk" but intent may be "window average") | Low (confirmed in architecture 12 Open Questions) | Low (chroma_entropy is not used in Horizon 1 prompt builder) | H1.S03 | Architecture doc explicitly confirms point-in-time interpretation is correct. Test fixtures test entropy on a single chroma vector. |
| `demo/start` endpoint fails to exercise trajectory features because it processes one chunk per file | Low (now mitigated by explicit work item requiring full chunk iteration) | High (demo appears broken at hackathon — indicators never populate in demo mode) | H1.S06 | Iterate all chunks via `load_and_chunk` generator. `test_demo_start_broadcast_includes_indicators_field` asserts the null→populated transition across the emitted frame sequence. |

---

## 7. Requirements Traceability — All AC IDs Mapped

| AC ID | FR Ref | Closed By Slice(s) |
|-------|--------|---------------------|
| AC-01 Layer 1 keys present | FR-01 | H1.S02 (implementation), H1.S02 (tests) |
| AC-02 Layer 1 latency | FR-01 | H1.S01 (benchmark measurement) |
| AC-03 Layer 2 indicators computed | FR-02 | H1.S03 (implementation + tests) |
| AC-04 Layer 2 cold start | FR-02 | H1.S03 (cold-start tests) |
| AC-05 Layer 2 latency < 50ms | FR-02 | H1.S03 (`test_latency_under_50ms`) |
| AC-06 Prompt v2 trajectory descriptors present | FR-03 | H1.S04 (unit tests), H1.S05 (integration test) |
| AC-07 Prompt v2 cold-start fallback | FR-03i | H1.S04 (`test_cold_start_none_indicators`, `test_cold_start_unavailable_indicators`) |
| AC-08 Prompt v2 output is valid MusicGen input | FR-03j | H1.S04 (`test_output_is_nonempty_string`, `test_output_no_newlines_or_json`) |
| AC-09 Existing consumers unaffected | US-05 | H1.S02 (`test_v1_keys_preserved`), H1.S04 (`test_v1_prompt_callable_on_new_featurevector`), H1.S06 (WS JSON additivity test), H1.S08 (full regression run) |
| AC-10 UI trend indicators displayed | US-04 | H1.S07 (implementation), H1.S06 (WS payload delivers indicators) |

All 10 acceptance criteria from `01-REQUIREMENTS.md` are covered. No orphaned ACs.

All MUST functional requirements covered:
- FR-01 (Layer 1 widening): H1.S02
- FR-02 (Layer 2 indicators): H1.S03
- FR-03 (Prompt builder v2): H1.S04 + H1.S05
- FR-04 (Window size configurability — SHOULD): `HORIZON1_WINDOW_N` env var implemented in H1.S03 per architecture
- FR-05 (Layer 2 availability signaling — SHOULD): `indicators: null` in WS frame (H1.S06) + warm-up state in UI (H1.S07)

---

## 8. Out of Scope for Horizon 1 (Deferred)

The following are explicitly NOT in any slice and MUST NOT be implemented during the Horizon 1 forge sprint:

| Item | Deferred To |
|------|------------|
| Layer 3 structural signals (self-similarity matrix, novelty detection, phrase length, energy arc position, harmonic tension, repetition/novelty scores) | Horizon 2 |
| Layer 4 interaction alpha signals (engagement prediction, intent classification, fatigue detection, session arc model) | Horizon 3 |
| Session logging infrastructure (storing full feature+generation+timestamp tuples for offline training) | Horizon 2 pre-work |
| CENS feature (`librosa.feature.chroma_cens`) | Deferred (OQ-01 resolved as out of scope) |
| `percussive_ratio` as a separate key | Deferred (derivable as `1 - harmonic_ratio` if needed) |
| `mfcc_delta` / `mfcc_delta_delta` (13-dim delta arrays) | Future Horizon 1 extension |
| `spectral_bollinger` (Bollinger band position of centroid) | Future Horizon 1 extension |
| Layer 2 SHOULD indicators: `bpm_ma`, `energy_volatility`, `key_change_rate`, `onset_density`, `harmonic_percussive_ratio` trend, `flux_trend`, `dynamic_range` | Future Horizon 1 extension |
| History ring expansion beyond 30 entries | Architecture constraint; unchanged in Horizon 1 |
| Per-indicator configurable window sizes | Single global `HORIZON1_WINDOW_N` is sufficient for Horizon 1 |
| Exporting Layer 2 indicators to the REST API (`GET /features/latest`, `GET /features/history`) | Deferred; indicators not persisted to store |
| New REST endpoints | Horizon 1 makes zero REST endpoint changes |
| UI restructuring (new pages, new layout sections, interactive charts, tooltips beyond `title` attribute, dark/light mode toggle) | Not in scope per TD decision OQ-07 |
| Per-indicator drill-down views, configuration UI for thresholds or window size | Not in scope |
| Display of raw float values for `spectral_trend` or `energy_momentum` | Only derived representations (arrow symbol, regime string) are shown |
| Indicators beyond the four UI elements: `chroma_entropy`, `chroma_volatility`, `key_stability`, `onset_regularity`, `bpm_volatility`, `energy_momentum` do not appear in the UI | Not in scope per `03-UI-SPEC.md` Section 1 |

---

## 9. Slice Summary — Count and Complexity

| Slice | Title | Complexity | Primary Output |
|-------|-------|------------|---------------|
| H1.S01 | Latency Benchmark | S | `benchmarks/horizon-1-layer-1-latency.md`, `scripts/benchmark_layer1.py` |
| H1.S02 | Layer 1 Widening + Thresholds | M | `src/features/engine.py` (modified), `src/features/thresholds.py` (new) |
| H1.S03 | Layer 2 Indicators Module | M | `src/features/indicators.py` (new), `tests/test_indicators.py` (new) |
| H1.S04 | Prompt Builder v2 | M | `src/generation/prompt_v2.py` (new), `tests/test_prompt_v2.py` (new) |
| H1.S05 | GenerationEngine Wiring | S | `src/generation/engine.py` (modified) |
| H1.S06 | WebSocket Payload Extension | S | `src/api/app.py` (modified) |
| H1.S07 | Web UI — Indicator Elements | M | `ui/index.html`, `ui/app.js`, `ui/style.css` (all modified) |
| H1.S08 | Polish + Integration Verification | S | No new files; test suite passes, `CLAUDE.md` updated |

**Total slices:** 8
**New test files:** 2 (`tests/test_indicators.py`, `tests/test_prompt_v2.py`)
**New production files:** 3 (`src/features/indicators.py`, `src/features/thresholds.py`, `src/generation/prompt_v2.py`)
**Modified production files:** 4 (`src/features/engine.py`, `src/generation/engine.py`, `src/api/app.py`, `ui/` trio)
**New script/artifact files:** 2 (`scripts/benchmark_layer1.py`, `benchmarks/horizon-1-layer-1-latency.md`)

---

## 10. Open Questions

These items cannot be fully resolved from the three spec documents and are flagged for Danny/Quincy before or during implementation:

**OQ-PLAN-01: RESOLVED** — H1.S01 benchmark emits raw flux p95 and recommends a `FLUX_NORM_DIVISOR` value in a dedicated 'Raw Spectral Flux Calibration' section. H1.S02 Preconditions require `FLUX_NORM_DIVISOR` to be set to that benchmark-recommended value before writing `test_spectral_flux_range`. The test-ordering trap (divisor=1.0 makes range test trivially pass while real music clips to 1.0) is closed.

**OQ-PLAN-02: RESOLVED** — `test_spectral_contrast_finite` added to H1.S02 test list. Asserts all values in the `spectral_contrast` list are finite floats (no NaN/Inf) across silent, sine, and noise fixtures. No range assertion is required since `spectral_contrast` is log-ratio in dB and is not normalized.

**OQ-PLAN-03: `onset_regularity` behavior with short history windows**

With `HORIZON1_WINDOW_N = 10`, the `onset_strength` series passed to autocorrelation has length 10. The autocorrelation peak detection at "lag 1 or 2" may not be musically meaningful at this window size (10 chunks × ~2s = ~20 seconds of audio; the beat period at 120 BPM is ~0.5s, which is 4 chunks). The implementer should verify that the autocorrelation result is useful at this window size during H1.S08 play-testing. If `onset_regularity` consistently returns near-zero for periodic music, the indicator may need a different lag search strategy (e.g., look at lags 2–5 instead of just 1–2). This is a calibration concern, not a blocking spec gap.

**OQ-PLAN-04: RESOLVED** — Snapshot test `test_snapshot_full_trajectory` follows capture-after-impl TDD: stub `expected=""` initially, implement `build_prompt_v2`, run to capture actual output, assert stability, commit the captured snapshot. TDD note embedded in the H1.S04 work items list above.

---

## 11. Sequence Rules

1. Complete each slice fully — all tests passing — before starting any dependent slice.
2. H1.S01 is not optional. Do not write Layer 1 production code without the benchmark report.
3. If the benchmark triggers the amendment path (HPSS removed from MUST): update the implementation plan for H1.S02 accordingly (6 features instead of 7) and note the amendment in `benchmarks/horizon-1-layer-1-latency.md` before proceeding.
4. H1.S03 and H1.S04 may be worked in parallel (no shared file ownership). Coordinate on the indicator dict shape if ambiguous.
5. If blocked on any slice: document the blocker. Do not skip ahead to a dependent slice.
6. `make test` must pass after each slice before the next begins. No accumulated broken tests.
7. No features beyond what is listed in the slices. If Danny identifies a new indicator or UI element during play-testing, it goes into a Horizon 1.1 scope document, not into this sprint.

---

*Roadmap by: @planner*
*Inputs: specs/horizon-1/01-REQUIREMENTS.md, specs/horizon-1/02-ARCHITECTURE.md, specs/horizon-1/03-UI-SPEC.md, specs/03-ROADMAP.md (style reference), specs/04-HORIZONS.md (scope sanity check)*
*Status: READY FOR FORGE*
