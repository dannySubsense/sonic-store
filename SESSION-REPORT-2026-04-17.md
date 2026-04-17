# Session Report — 2026-04-17 (Horizon 1)
**From:** Quincy (Technical Director)
**To:** Danny (Composer)
**Session duration:** ~4 hours (picked up from 2026-04-16 late evening)
**Status:** Horizon 1 shipped, ahead of schedule

---

## What Happened

One session, two orchestrations, one shipped feature.

### Part 1 — Spec (`/spec-start`)

Produced the full Horizon 1 spec bundle at `specs/horizon-1/`:

| Doc | Purpose | Lines |
|-----|---------|-------|
| 01-REQUIREMENTS.md | User stories, FR/NFR, 10 ACs, 13 edge cases, 7 OQs | 316 |
| 02-ARCHITECTURE.md | Module map, Layer 1/2 design, prompt v2, WS payload, latency budget | 885 |
| 03-UI-SPEC.md | 4 additive UI elements: 2 sparklines, regime pill, spectral arrow | 443 |
| 04-ROADMAP.md | 8 slices, benchmark-first, dependency graph, requirements traceability | 722 |
| 05-REVIEW.md | Two-pass audit (12 gaps found → all closed) + Frank's re-review | 544 |

Scope: widen Layer 1 from 6 → 13 librosa features (added `spectral_rolloff_hz`, `spectral_flux`, `spectral_contrast`, `zero_crossing_rate`, `mfcc`, `harmonic_ratio`, `tonnetz`). Introduce Layer 2: 9 temporal indicators computed from the 30-entry history ring. Evolve prompt builder v1 → v2 with trajectory phrases.

### Part 2 — Senior QC Pass 1 (Frank)

Frank reviewed the spec bundle and returned **APPROVE-WITH-CONDITIONS**, naming 3 concrete fixes:

1. **Demo warm-up** — `/demo/start` called `next(chunks)` (one chunk per file), so history never reached N=10 and indicators stayed `null` throughout any demo. Frank's call: either iterate all chunks or scope-exclude.
2. **`warming_up_chunks_remaining` drift** — prose in `02-ARCHITECTURE.md §4.5` referenced a field that `_cold_start_result()` never returned.
3. **`FLUX_NORM_DIVISOR` test-ordering trap** — `H1.S02`'s range test would trivially pass at placeholder divisor=1.0 while real music clips to 1.0.

TD decisions: (1) iterate all chunks; (2) drop prose; (3) H1.S01 emits raw flux p95, H1.S02 HALTs until divisor calibrated.

All three closed in a parallel fix pass. Frank's pass-2 review: **APPROVE**.

### Part 3 — Forge (`/forge-start`)

All 8 slices through build-test-verify:

| Slice | Outcome |
|-------|---------|
| H1.S01 Benchmark | PASS — combined p95 339.91ms / 500ms budget. `FLUX_NORM_DIVISOR = 203820.109375` recommended from raw flux p95 across music-like fixtures. Ran on QEMU (not RTX 5090 — re-run flagged for rehearsal). |
| H1.S02 Layer 1 widening | 7 new keys added to `extract_features()`, shared HPSS decomposition. +12 tests. 77/77 suite. |
| H1.S03 Layer 2 indicators | New `compute_indicators(history, window)`. 1 implementation bug caught by test-writer: cold-start gate ran before window clamp, preventing clamp-to-30 behavior. Fixed. +16 tests. 93/93 suite. |
| H1.S04 Prompt builder v2 | Inline-duplicated v1 helpers, trajectory phrase assembly. +13 tests. 106/106 suite. Snapshot test captured. |
| H1.S05 GenerationEngine wiring | 3-line loop body change. +2 tests. 108/108 suite. |
| H1.S06 WS payload + demo_start | `mic_loop` and `demo_start` both broadcast indicators. `demo_start` iterates ALL chunks (Frank's demo-critical fix). +3 tests. 111/111 suite. |
| H1.S07 Web UI | 4 DOM elements, 6 CSS classes, 3 JS functions, 2 SYNC comments. No pytest (manual verification deferred to rehearsal per roadmap). |
| H1.S08 Polish | Full suite pass + REST E2E verified (`GET /features/latest` → 20 keys). CLAUDE.md updated, benchmark post-impl section appended. |

### Part 4 — Senior QC Pass 2 (Frank, Code Review)

Frank read the actual source and flagged:
- **#1 (blocking before demo):** `demo_start` ran `extract_features` on the event loop — `mic_loop` correctly offloads to a thread pool. ~300ms blocks × 15 chunks = bursty broadcasts instead of smooth 2s-cadence UI.
- **#2 (known-unknown):** History mixes sources across demo→mic transitions. First ~20s of mic indicators use partial demo data. Session-hygiene note.
- **#3 (minor):** `_EPS = 1e-12` in `energy_regime` — spec deviation of 10 orders of magnitude below the threshold. Non-issue.

Fix #1 applied: `extract_features(chunk, source="file")` wrapped in `loop.run_in_executor(None, lambda c=chunk: ...)`. 111/111 tests still pass. Frank signed off.

(Frank separately called out that I'd overstated the fix as "one-line" when the diff was six lines. Correct call. Acknowledged.)

### Part 5 — Ship

`32ce86f` on `main`, pushed to `dannySubsense/sonic-store`. 25 files, 4,980 insertions, 13 deletions.

---

## Numbers

- **Tests:** 68 (v1) → **111** (+43 new across 5 test files). Zero regressions.
- **Spec bundle:** 5 docs, ~2,910 lines. Two reviewer passes + two Frank passes.
- **Production code added:** 3 new modules (`indicators.py`, `thresholds.py`, `prompt_v2.py`), 4 modified (`engine.py`, `generation/engine.py`, `api/app.py`, `ui/` trio).
- **FeatureVector schema:** 13 keys → 20 keys (additive).
- **WebSocket payload:** adds `"indicators": dict | null`. Backward-compat preserved via JSON additivity.
- **Store schema:** zero change. Layer 2 is derived, not persisted.

---

## What's Different Now

The prompt string going to MusicGen is no longer a frozen snapshot:

Before (v1):
> "energetic, driving balanced musical accompaniment, upbeat, 124 BPM, D minor, complementary to the input melody, instrumental"

After (v2 with indicators):
> "energetic, driving balanced musical accompaniment, fast, 130 BPM, D major, building energy, accelerating, harmonically stable in D major, brightening timbre, complementary to the input melody, instrumental"

The UI now shows trajectory visually: BPM and energy sparklines grow from chunk 1, regime pill lights up at chunk 10 (rising/falling/stable with color), spectral arrow flips ↑/→/↓ on centroid movement.

---

## Known Unknowns (Not Blocking, Validate in Rehearsal)

1. **Benchmark ran on QEMU, not RTX 5090.** If QEMU hits 339ms p95, the ROG Strix should be faster. Re-run in rehearsal to confirm.
2. **`onset_regularity` at N=10.** 10 chunks × 2s = 20s of very coarse onset data. Autocorrelation peak detection at this resolution may produce meaningless values for typical music. Validate with real audio; consider lag search strategy adjustment if the signal is uninformative.
3. **`v1 build_prompt` `print()` side effect.** `src/generation/prompt.py:63` prints every fallback. Cosmetic log noise during cold-start. Clean in a follow-up.
4. **Source-mixed history.** If demo mode runs before live mic in same session, first ~20s of mic indicators blend file+mic data. Either reset store on mic start or filter history by `source`. Post-hackathon.
5. **Demo WAVs.** `demo/` has only `README.txt`. Need ≥1 WAV file (10+ seconds for indicator warm-up) before the demo endpoint does anything visible.

---

## Tools That Worked

- **`/spec-start` + spec-reviewer in a loop:** Two automated review passes caught 12 gaps (2 HIGH, 6 MEDIUM, 4 LOW) that would have bitten during forge.
- **`/senior-qc` (Frank) independently after reviewer approval:** Found 3 more gaps the reviewer missed, all product-critical. The demo warm-up gap would have been a hackathon-day surprise.
- **`/forge-start` end-to-end autonomous:** 8 slices through build-test-verify-approve-commit with minimal human handholding. Caught 2 implementation bugs via agent handoff (window-clamp order, `demo_start` executor wrap).
- **Benchmark-as-gate slice (H1.S01):** Frank's demand for calibrated `FLUX_NORM_DIVISOR` before tests were written prevented a broken-binary-flag bug from shipping.

---

## Next Session

1. **Dogfood on RTX 5090 demo hardware** — re-run benchmark, play with the feature, observe indicator behavior on real music.
2. **Drop demo WAVs** into `demo/` directory.
3. **Validate `onset_regularity`** semantics empirically during play-testing.
4. (Post-rehearsal) Horizon 2 spec: learned features + session logging infrastructure.

---

*Session by: Quincy (Technical Director) + Danny (Composer)*
*Co-author on commits: Claude Opus 4.7 (1M context)*
*Status: Horizon 1 COMPLETE. Ready for dogfood.*
