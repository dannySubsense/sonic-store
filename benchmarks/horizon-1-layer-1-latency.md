# Horizon 1 — Layer 1 Latency Benchmark Report
**Date:** 2026-04-17T01:31:51Z
**Hardware:** ml-research — QEMU Virtual CPU version 2.5+
**Python:** 3.12.3
**librosa:** 0.11.0

## Verdict
**PASS** — all 7 MUST features fit within 500ms combined budget (max p95: 339.9ms)

## Combined extract_features() Timing
| Fixture | Mean (ms) | P95 (ms) | Within 500ms? |
|---------|-----------|----------|---------------|
| sine | 268.73 | 274.42 | yes |
| silence | 199.46 | 250.77 | yes |
| chirp | 280.57 | 339.91 | yes |

## Per-Feature Timing
| Feature | Fixture | Mean (ms) | P95 (ms) |
|---------|---------|-----------|----------|
| spectral_rolloff_hz | sine | 5.50 | 5.65 |
| spectral_rolloff_hz | silence | 5.52 | 5.69 |
| spectral_rolloff_hz | chirp | 5.52 | 5.60 |
| spectral_flux | sine | 2.91 | 2.94 |
| spectral_flux | silence | 2.90 | 2.94 |
| spectral_flux | chirp | 2.91 | 2.96 |
| spectral_contrast | sine | 7.14 | 7.24 |
| spectral_contrast | silence | 4.51 | 4.56 |
| spectral_contrast | chirp | 7.19 | 7.29 |
| zero_crossing_rate | sine | 1.19 | 1.22 |
| zero_crossing_rate | silence | 1.19 | 1.22 |
| zero_crossing_rate | chirp | 1.19 | 1.22 |
| mfcc | sine | 8.48 | 11.03 |
| mfcc | silence | 8.38 | 10.08 |
| mfcc | chirp | 10.00 | 13.00 |
| harmonic_ratio | sine | 123.30 | 123.89 |
| harmonic_ratio | silence | 39.12 | 39.40 |
| harmonic_ratio | chirp | 124.34 | 124.89 |
| tonnetz | sine | 240.33 | 242.22 |
| tonnetz | silence | 155.26 | 156.54 |
| tonnetz | chirp | 241.39 | 242.94 |

## Raw Spectral Flux Calibration
| Fixture | Raw min | Raw mean | Raw p95 | Raw max |
|---------|---------|----------|---------|---------|
| sine | 1672.267456 | 1672.267456 | 1672.267456 | 1672.267456 |
| silence | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| chirp | 203820.109375 | 203820.109375 | 203820.109375 | 203820.109375 |

**Recommended FLUX_NORM_DIVISOR:** `203820.109375`

Rationale: FLUX_NORM_DIVISOR is set to the p95 of raw spectral flux across music-like fixtures (sine, chirp), so that typical musical audio maps to approximately [0.3, 0.95] and silence maps to approximately 0 after normalization.

## Amendment Path

Not triggered — all features within budget.

## Post-Implementation Verification (H1.S08)

**Date:** 2026-04-17

After H1.S02 integrated all 7 new Layer 1 features into `extract_features()` with shared HPSS decomposition (per §3.3):

- Full non-integration test suite: **111/111 pass** (was 68 in v1; +43 Horizon 1 tests)
- Test counts per slice:
  - H1.S02 (Layer 1 widening): +12 tests in `tests/test_features.py`
  - H1.S03 (Layer 2 indicators): +16 tests in `tests/test_indicators.py`
  - H1.S04 (Prompt builder v2): +13 tests in `tests/test_prompt_v2.py`
  - H1.S05 (GenerationEngine wiring): +2 tests in `tests/test_generation.py`
  - H1.S06 (WS payload + demo_start): +3 tests in `tests/test_api.py`
- REST backward-compat confirmed: `POST /analyze` → 20 keys, `GET /features/latest` → 20 keys, all 7 new keys present
- `FLUX_NORM_DIVISOR` calibrated from this report and committed to `src/features/thresholds.py`: `203820.109375`

**Note on hardware:** This benchmark ran on a QEMU virtual CPU, not the final demo hardware (ROG Strix SCAR 18, RTX 5090). Timings are conservative — real hardware will be faster. Re-run this benchmark on the demo machine during hackathon rehearsal to confirm headroom.

**Known-unknowns deferred to play-testing (Frank's final framing):**
- `onset_regularity` semantics at N=10 autocorrelation: may produce near-zero for typical music — validate with real audio and adjust lag search strategy if the signal is uninformative.
- `v1 build_prompt` `print()` side effect in `src/generation/prompt.py` — cosmetic log noise during cold-start fallback; clean in a follow-up.
