# Horizon 1 — Spec Bundle Review
**Version:** 1.0
**Date:** 2026-04-16
**Status:** COMPLETE
**Author:** @spec-reviewer
**Inputs:** `specs/horizon-1/01-REQUIREMENTS.md`, `specs/horizon-1/02-ARCHITECTURE.md`, `specs/horizon-1/03-UI-SPEC.md`, `specs/horizon-1/04-ROADMAP.md`
**Context:** `specs/00-DECISIONS.md`, `specs/02-ARCHITECTURE.md`, `specs/05-SONIC-ALPHA.md`, `CLAUDE.md`, `src/generation/prompt.py`, `src/api/app.py`

---

## 1. Executive Verdict

**APPROVE-WITH-FIXES.**

The four Horizon 1 spec documents are coherent, traceable, and internally consistent on the high-level design. All ten acceptance criteria have a home in architecture, UI (where relevant), and roadmap. The TD decisions OQ-01 through OQ-07 are respected end-to-end. No Layer 3 or Layer 4 scope creep. The v1 contract (store interface, REST endpoints, v1 `build_prompt`) is preserved by construction.

However, the bundle has a small set of implementation-level precision gaps the forge agent will hit within the first 30 minutes of Slice 02 or 04 unless they are tightened now. Most are low-severity symbol-name, threshold-source-of-truth, and cold-start-sentinel mismatches between documents. None are blockers; all are resolvable with small edits to `02-ARCHITECTURE.md` and `03-UI-SPEC.md`. See Section 4 for the gap list and Section 9 for the ordered fix actions.

Gap count by severity: **0 BLOCKER / 2 HIGH / 6 MEDIUM / 4 LOW.**

---

## 2. Consistency Matrix — AC to Arch to UI to Slice

Ten acceptance criteria from `01-REQUIREMENTS.md` crossed against the other three documents.

| AC | Addressed in 02-ARCHITECTURE.md | Addressed in 03-UI-SPEC.md | Slice + Test in 04-ROADMAP.md |
|----|--------------------------------|---------------------------|-------------------------------|
| AC-01 Layer 1 keys present | §3.1 new keys table, §3.2 per-feature computation | N/A (no UI exposure) | H1.S02 — `test_layer1_new_keys_present`, `test_*_range`, `test_*_shape`, `test_v1_keys_preserved` |
| AC-02 Layer 1 extraction latency <500ms | §9.2 latency table, benchmark flagged to roadmap | N/A | H1.S01 — benchmark artifact (`benchmarks/horizon-1-layer-1-latency.md`) |
| AC-03 Layer 2 indicators computed | §4.1–4.4 module + per-indicator computation | N/A (computed server-side) | H1.S03 — `test_warm_exactly_n_entries` plus per-indicator tests |
| AC-04 Layer 2 cold start | §4.5 cold-start result; sentinel dict | §2 "Indicator Availability Signal" + §8 state table | H1.S03 — `test_cold_start_empty_history`, `test_cold_start_one_entry`, `test_cold_start_n_minus_one` |
| AC-05 Layer 2 latency <50ms | §9.3 latency estimate | N/A | H1.S03 — `test_latency_under_50ms` |
| AC-06 Prompt v2 trajectory descriptors | §6.4 descriptor selection table | §6 prompt display (natural-language passthrough) | H1.S04 unit tests + H1.S05 `test_generation_v2_prompt_with_history` |
| AC-07 Prompt v2 cold-start fallback | §6.3 gate: `indicators is None or not available` | N/A | H1.S04 — `test_cold_start_none_indicators`, `test_cold_start_unavailable_indicators` + H1.S05 `test_generation_v2_cold_start_prompt` |
| AC-08 Prompt v2 valid MusicGen input | §6.6 output invariants | §6 (prompt renders in `#ai-prompt` `textContent`) | H1.S04 — `test_output_is_nonempty_string`, `test_output_no_newlines_or_json` |
| AC-09 Existing consumers unaffected | §10 backward-compat contract a-e | §6 "No changes to prompt display element are needed" | H1.S02 (`test_v1_keys_preserved`), H1.S04 (`test_v1_prompt_callable_on_new_featurevector`), H1.S06 WS JSON test, H1.S08 regression |
| AC-10 UI trend indicators displayed | §7.2 WS payload (shape), §7.5 UI handler overview | §3.1–3.4 all four UI elements + §8 state visibility | H1.S06 (WS payload) + H1.S07 (UI manual test checklist) |

All ten rows populated. No `MISSING` cells in the traceability matrix.

One narrow observation: AC-10 is satisfied by **manual** UI test checklist in H1.S07 rather than an automated test. This matches the v1 pattern from S07 (which also had no UI pytest), and the roadmap explicitly states that; documenting here so Danny does not expect automated coverage for the sparkline visuals.

---

## 3. Contradiction Scan

Every cross-document disagreement found during the review.

### C-01 (HIGH) — `KEY_NAMES` symbol does not exist in v1 `prompt.py`

`02-ARCHITECTURE.md` §6.5 states:
> "The `_energy_descriptor`, `_timbre_descriptor`, `_tempo_descriptor`, and `KEY_NAMES` are imported from `src/generation/prompt.py`"

The actual symbol in `src/generation/prompt.py` is `_KEY_NAMES` (leading underscore, module-private by PEP 8 convention). The descriptor helpers are likewise `_tempo_descriptor`, `_energy_descriptor`, `_timbre_descriptor`. The roadmap H1.S04 work items repeat this claim verbatim:
> "Import `KEY_NAMES` and descriptor helper functions from `src/generation/prompt.py` (extract to module-level helpers if they are currently inline; if they are already module-level, import directly)"

This is a name mismatch that will cause an `ImportError` the moment `prompt_v2.py` is written. The parenthetical "extract to module-level helpers if they are currently inline" is moot — they are already module-level. The issue is that they are `_`-prefixed. Either:
- Option A: Rename them in `prompt.py` to remove underscores (breaks v1 encapsulation convention but is trivial), or
- Option B: Duplicate the small constants and three-line descriptor fns inside `prompt_v2.py` (no import at all), or
- Option C: Import the underscore-prefixed names explicitly (`from src.generation.prompt import _KEY_NAMES as KEY_NAMES, _tempo_descriptor, ...`) — works but reads badly.

Recommendation: Option B. The lookup functions are 3 lines each. Duplicating them in `prompt_v2.py` avoids reaching into `_`-prefixed module internals.

### C-02 (HIGH) — WS `indicators` field: `null` vs `{available: False, ...}`

The four docs are inconsistent about what travels on the wire during cold-start.

- `01-REQUIREMENTS.md` AC-04 says Layer 2 returns "a result indicating indicators are unavailable (e.g., all None, or a `{"available": False}` dict)"
- `02-ARCHITECTURE.md` §4.2 says the function returns `{"available": False, ...all None}`
- `02-ARCHITECTURE.md` §7.2 then says the WS frame's `"indicators"` field is "`null` when `compute_indicators` returns `{"available": False, ...}`"
- `02-ARCHITECTURE.md` §7.4 encodes this: `ind_payload = indicators if indicators.get("available") else None`
- `03-UI-SPEC.md` §2 confirms UI reads `msg.indicators === null` as the canonical cold-start signal
- `04-ROADMAP.md` H1.S06 work items match §7.4

This **is** consistent between architecture/UI/roadmap once you trace it through — the function returns a `{"available": False}` dict, but `app.py` converts it to `None` before broadcasting. Good.

**But**: `02-ARCHITECTURE.md` §6.3 has `build_prompt_v2` read the dict directly (`indicators.get("available", False)`), **not** `None`. That means the v2 prompt builder and the UI consume the Layer 2 signal in incompatible forms — prompt builder expects a dict (because it is called inside the generation thread where `compute_indicators` output is unfiltered), UI expects `None` (because `app.py` filters). That is OK and actually correct (different call sites), but this subtle asymmetry is not written down anywhere. A forge implementer reading only §6 + §7 would reasonably standardize on one and break the other.

Recommendation: Add a one-paragraph "Cold-start representations — two forms" note to `02-ARCHITECTURE.md` §4.5 or §7.2 explicitly stating:
- Inside the process: `{"available": False, ...all None}` dict (never `None`)
- Over the wire (WS): `null` after the `app.py` filter
- `build_prompt_v2` accepts either form (it checks `is None or not .get("available")`)

### C-03 (MEDIUM) — Threshold source of truth for spectral arrow

`02-ARCHITECTURE.md` §5 places `SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50.0` / `-50.0` in `src/features/thresholds.py` (Python, server-side, OQ-03 decision).

`03-UI-SPEC.md` §3.3 says the UI must classify `spectral_trend` using the same ±50 Hz/step threshold to pick the arrow symbol, and OQ-UI-02 explicitly acknowledges the UI hardcodes the value in `app.js`. `04-ROADMAP.md` H1.S07 likewise instructs the implementer to hardcode ±50.

This is a soft contradiction — two sources of truth for the same constant, one Python, one JS. The UI spec calls it an "implementation detail" and a "cosmetic issue if mismatched," which is true but slightly understates the drift risk: Danny calibrates the server constant during play-testing (per the risk table), and the UI silently stops matching it. The arrow would then disagree with the server-driven prompt regime descriptors, which is a demo-quality concern.

Recommendation: Either (a) expose thresholds via `GET /status` so the UI fetches them once on connect (10 LOC of server work; matches the extensibility pattern already in `app.py`), or (b) accept the drift and add a `// SYNC WITH src/features/thresholds.py` comment beside the JS constant so a future engineer knows. Option (a) is minor and properly closes OQ-UI-02; option (b) is fine for the June demo.

### C-04 (MEDIUM) — Window N=10 stated multiple places; clamping rule only in one

`01-REQUIREMENTS.md` FR-04 says N is configurable with a documented default.
`02-ARCHITECTURE.md` §4.1 sets `HORIZON1_WINDOW_N = int(os.getenv("HORIZON1_WINDOW_N", "10"))` and §4.3 defines clamping: `min(window, 30, len(history))`, and additionally returns cold-start if `len(history) < HORIZON1_WINDOW_N`.
`03-UI-SPEC.md` §2 says the client sparkline buffer is capped at 10 to match `HORIZON1_WINDOW_N`.
`04-ROADMAP.md` H1.S03 has `test_window_clamp_beyond_30` for the upper-bound clamp.

Question: If a user sets `HORIZON1_WINDOW_N=5` via env, the UI sparkline buffer (hardcoded 10) and the server window (5) disagree. The server would emit indicators after 5 chunks but the sparkline wouldn't fill until 10. This is not a spec contradiction per se, but the UI spec frames its buffer size as *matching* the server window — it doesn't. It is a constant independent of the env var.

Recommendation: Either change the UI spec wording to "The sparkline buffer is fixed at 10 entries, which equals the default `HORIZON1_WINDOW_N`" (honest), or wire the buffer size to the same value on page load (but the UI can't read env vars, so this requires a `/status` surface).

### C-05 (MEDIUM) — `demo/start` broadcast path not updated in H1.S06 work items

`02-ARCHITECTURE.md` §7.4 final paragraph says:
> "The `demo_start` endpoint in `app.py` also broadcasts features. It should be updated with the same pattern."

`04-ROADMAP.md` H1.S06 work items mention this:
> "Apply the same pattern to the `demo/start` endpoint broadcast if it emits feature messages"

but provides no test for the demo path. `demo_start` is an important demo surface (per CLAUDE.md S11 "POST /demo/start"). If the `mic_loop` path is updated but the demo path is missed or broken, the `make test` suite will pass while the demo path is stale. Adding one asserting test would close this.

Recommendation: Add an explicit demo-path work item to H1.S06 ("update `demo_start` endpoint broadcast identically") and an asserting test `test_demo_start_broadcast_includes_indicators_field` in `tests/test_api.py`.

### C-06 (MEDIUM) — `mic_loop` is inside `run_in_executor` context; new `get_history` call site ambiguous

`02-ARCHITECTURE.md` §7.4 prose states:
> "The call happens inside `loop.run_in_executor` context already established for `extract_features`, or it can be called directly since it is fast enough to not block the event loop meaningfully (< 1ms). For clarity and consistency, it is called directly (not in executor) given its trivial latency."

Reading the actual `src/api/app.py` `mic_loop` (confirmed in v1 source): `extract_features` is run in executor, then `store.write` is called synchronously in the event loop, then `manager.broadcast` runs async. The architecture's §7.4 code block inserts `history = store.get_history(...)` and `indicators = compute_indicators(...)` between `store.write(features)` and the broadcast — meaning `compute_indicators` runs on the event loop. For 10 entries this is <5ms per §9.3, so it is fine, but the architecture's hedging prose ("or it can be called directly") leaves the forge agent guessing. The roadmap H1.S06 is also ambiguous: the pseudocode uses the sync call, which is correct but not called out.

Recommendation: Tighten §7.4 prose to a single decision: "`compute_indicators` is called directly on the asyncio event loop in `mic_loop`. Justified: <5ms per §9.3, well within the event-loop budget." Remove the "or in executor" alternative.

### C-07 (MEDIUM) — `mfcc` coefficients 1-13 vs 0-12 inconsistency

`01-REQUIREMENTS.md` FR-01 table says `mfcc` is `list[float], length 13` with note "Mean over time, coefficients 1-13".
`02-ARCHITECTURE.md` §3.2 `mfcc` block says:
> "The zeroth coefficient (energy) is included as `mfcc[0]` for completeness; the requirements spec 'coefficients 1-13' refers to the 13-element vector not the exclusion of coefficient zero."

The architecture retcons the requirement text rather than flagging it. Librosa's `librosa.feature.mfcc(..., n_mfcc=13)` returns coefficients 0 through 12 (size 13), which is what the architecture wants. The requirement text "coefficients 1-13" is technically wrong — it should say "coefficients 0-12" or "13 coefficients including the zeroth (energy) coefficient."

This is a minor spec-text defect. It does not block implementation because the architecture pinned the behavior. But if a forge agent does a pedantic reading and tries to call `librosa.feature.mfcc(..., n_mfcc=14)[1:14]`, they would produce a different feature than either doc intended.

Recommendation: Edit `01-REQUIREMENTS.md` FR-01 row for `mfcc` to read "Mean over time, 13 coefficients (0-12), zeroth coefficient is signal energy."

### C-08 (LOW) — `spectral_contrast` range not bounded to [0,1] but no test enforces non-negativity

`02-ARCHITECTURE.md` §3.2 correctly notes `spectral_contrast` output is log-ratio in dB, typically `[0, 40]`, not normalized. `04-ROADMAP.md` H1.S02 `test_spectral_contrast_shape` checks length 7 only. `01-REQUIREMENTS.md` AC-01 says "spectral_contrast is a list of 7 floats" — also no range.

This is consistent across docs (all three permissibly silent on the range), but it leaves a gap for silent audio or pathological inputs where some band could be `0.0` or negative. Architecture §3.4 edge-case table does not list `spectral_contrast`. The planner flagged this (OQ-PLAN-02) as a test-design question.

Recommendation: Close OQ-PLAN-02 now by either adding `test_spectral_contrast_finite` (`all(math.isfinite(v) for v in spectral_contrast)`) to H1.S02, or explicitly document in architecture §3.4 that `spectral_contrast` for silent audio returns finite-but-unbounded values and the NaN/Inf guard only fires if librosa itself produces NaN.

### C-09 (LOW) — `chroma_entropy` semantics: window vs current chunk

`01-REQUIREMENTS.md` FR-02 table for `chroma_entropy` says "Computed From: chroma (current chunk)" — clear enough.
`02-ARCHITECTURE.md` §4.4 computes it from `history[0]["chroma"]`, which is consistent, and §12 "Open Architectural Questions" explicitly flags this for Quincy's confirmation. The planner's risk table (item 7) confirms the architecture's interpretation is correct.

This is not really a contradiction — it is resolved — but the architecture's own §12 still uses the word "worth confirming." It should be promoted to a locked decision. Otherwise the forge agent may re-open the question and implement both paths.

Recommendation: Replace §12 paragraph with a one-line statement: "`chroma_entropy` is computed on the current chunk's chroma (`history[0]`), per FR-02 and the mathematical definition of Shannon entropy on a probability distribution. The window-based dual is `chroma_volatility`."

### C-10 (LOW) — "Slice 1" terminology

`01-REQUIREMENTS.md` preamble says "TD decisions OQ-01 ... benchmark-first as Slice 1" per the task brief intro. The roadmap uses `H1.S01`. The rest of the bundle uses `H1.S01..H1.S08`. Just a stylistic note — no gap.

### C-11 (LOW) — Prompt v2 snapshot test and FLUX_NORM_DIVISOR loop

H1.S04 defines `test_snapshot_full_trajectory` with a hardcoded string. H1.S02 sets `FLUX_NORM_DIVISOR = 1.0` as a placeholder; H1.S08 may update it. If the divisor changes between S02 and S08, the snapshot test written in S04 (which does not depend on spectral_flux directly — confirmed, snapshot is about prompt output) is unaffected. But per OQ-PLAN-04, the snapshot string cannot be written until `build_prompt_v2` is implemented and stable. The roadmap does not call out that this is a "write test last in S04" pattern.

Recommendation: Add one sentence to H1.S04 work items: "Write `test_snapshot_full_trajectory` with an empty expected string stub, run the test, capture the actual output, commit it as the expected value. This is the documented TDD workflow for snapshot-style regression tests."

---

## 4. Gaps Table

| # | Gap | Lives In (or should) | Severity | Suggested Fix |
|---|-----|----------------------|----------|---------------|
| G-01 | `KEY_NAMES` / descriptor helpers imported from `src/generation/prompt.py` but actual symbols are `_`-prefixed | `02-ARCHITECTURE.md` §6.5, `04-ROADMAP.md` H1.S04 | HIGH | Use Option B: inline-duplicate the small helpers in `prompt_v2.py`. Update architecture text and roadmap work item. |
| G-02 | Cold-start representation drift (`{"available":False,...}` dict inside process vs `null` on WS) not called out | `02-ARCHITECTURE.md` §4.5 and §7.2 | HIGH | Add a "Cold-start representations — two forms" clarification paragraph (see C-02 above). |
| G-03 | Threshold source of truth: server has `thresholds.py`, UI hardcodes same values in `app.js` | `03-UI-SPEC.md` §3.3 OQ-UI-02, `02-ARCHITECTURE.md` (future `/status` hook) | MEDIUM | Either expose thresholds via `/status` for UI consumption (preferred), or lock a `// SYNC WITH src/features/thresholds.py` comment in `app.js`. Close OQ-UI-02 either way. |
| G-04 | UI sparkline buffer length (10) hardcoded, independent of `HORIZON1_WINDOW_N` env var | `03-UI-SPEC.md` §2 | MEDIUM | Update UI spec wording to acknowledge the buffer is fixed-size (not driven by env). OR expose the window via `/status`. |
| G-05 | `demo/start` broadcast update mentioned but no explicit test | `04-ROADMAP.md` H1.S06 | MEDIUM | Add `test_demo_start_broadcast_includes_indicators_field` to H1.S06 work items. |
| G-06 | `mic_loop` `compute_indicators` call site: architecture hedges between executor and direct call | `02-ARCHITECTURE.md` §7.4 | MEDIUM | Tighten prose to a single decision: direct call on asyncio loop (justified by <5ms latency). |
| G-07 | `mfcc` coefficient-range text inconsistent between requirements ("coefficients 1-13") and architecture ("includes zeroth") | `01-REQUIREMENTS.md` FR-01 | MEDIUM | Edit requirement to say "13 coefficients (0-12), zeroth coefficient is signal energy." |
| G-08 | `spectral_contrast` unbounded range but no finite-value test | `04-ROADMAP.md` H1.S02 | LOW | Add `test_spectral_contrast_finite` to H1.S02 OR document finite-but-unbounded in architecture §3.4. Closes OQ-PLAN-02. |
| G-09 | `chroma_entropy` semantics flagged as "worth confirming" in architecture §12 | `02-ARCHITECTURE.md` §12 | LOW | Replace §12 text with a locked statement. Semantics are current-chunk; `chroma_volatility` is the window-based dual. |
| G-10 | Prompt v2 snapshot test workflow not documented (chicken-and-egg with the expected string) | `04-ROADMAP.md` H1.S04 | LOW | Add one-sentence TDD note: stub empty expected, implement, capture, commit. Addresses OQ-PLAN-04. |
| G-11 | No gap — intentional | — | — | (reserved) |
| G-12 | UI "four elements" include BPM sparkline but BPM trend is text-only ("↑/→/↓" arrow is for spectral only), whereas AC-10 says "at least one trend indicator ... is visible for `energy_regime` **and** `delta_bpm`" | `03-UI-SPEC.md` §1 vs `01-REQUIREMENTS.md` AC-10 | MEDIUM | Confirm: the BPM sparkline shape IS the `delta_bpm` trend indicator per UI spec §1 scope. This is a satisfactory reading (a sparkline "is" a trend indicator), but the BPM sparkline draws from `msg.data.bpm`, not from `indicators.delta_bpm`. A pedantic reading of AC-10 might expect a directional arrow or numeric indicator for BPM specifically. Add one sentence to UI spec §1 clarifying that BPM trend visibility is achieved by the sparkline's visible slope, not by a separate arrow on BPM. |

---

## 5. Research Validity / Framework Fidelity Check

Cross-checked the four Horizon 1 documents against `specs/05-SONIC-ALPHA.md` (the 4-layer framework).

**Layer 1 widening — confirmed correct scope.** The seven MUST features selected (`spectral_rolloff_hz`, `spectral_flux`, `spectral_contrast`, `zero_crossing_rate`, `mfcc`, `harmonic_ratio`, `tonnetz`) are all on `05-SONIC-ALPHA.md`'s Layer 1 table and all available in librosa per `specs/05-SONIC-ALPHA.md §4 "Immediate value, established math, no ML required"`. The two excluded SHOULD features (`cens`, `percussive_ratio`) are explicitly deferred — consistent with the framework's note that percussive is derivable as `1 - harmonic_ratio`.

**Layer 2 MUST set — confirmed correct scope.** The nine indicators (`delta_bpm`, `bpm_volatility`, `energy_momentum`, `energy_regime`, `chroma_entropy`, `chroma_volatility`, `key_stability`, `spectral_trend`, `onset_regularity`) all appear in `05-SONIC-ALPHA.md`'s Layer 2 table. The deferred SHOULD set (`bpm_ma`, `energy_volatility`, `key_change_rate`, `spectral_bollinger`, `onset_density`, `mfcc_delta`, `harmonic_percussive_ratio` trend, `flux_trend`, `dynamic_range`) likewise aligns.

**No Layer 3 scope creep.** Zero mentions of self-similarity matrix, novelty detection, phrase length, energy arc position, harmonic tension, repetition/novelty scores, convergence forecasting, exploration score, return probability, or surprise index in any of the four Horizon 1 docs except as explicit OUT-OF-SCOPE items. Confirmed clean.

**No Layer 4 scope creep.** Zero mentions of engagement prediction, intent classification, response preference, influence direction, harmonic convergence, energy mirroring, novelty utility, fatigue detection, creative temperature, or session arc model. Confirmed clean.

**Formula fidelity.** Three formulas referenced with source attribution:
- Delta formula attributed to **Davis & Mermelstein 1980** in `01-REQUIREMENTS.md` FR-02, `02-ARCHITECTURE.md` §4.4, and `05-SONIC-ALPHA.md` §1. Matches research bibliography entry [8]. Correct.
- Shannon entropy formula $H = -\sum p_i \log p_i$ in `01-REQUIREMENTS.md` FR-02 and `02-ARCHITECTURE.md` §4.4 — standard, no attribution needed.
- Spectral flux $\sum_k (|X_t[k]| - |X_{t-1}[k]|)^2$ in `01-REQUIREMENTS.md` FR-01 — matches `05-SONIC-ALPHA.md` Layer 1 formulas; Bello 2005 [16] is the canonical reference but not cited in the Horizon 1 docs. Low-severity research-citation cosmetic.
- Krumhansl-Schmuckler key detection is mentioned only as an existing v1 dependency (not re-introduced). Consistent.

**Framework fidelity is clean.** The bundle is faithful to the 4-layer model.

---

## 6. Constraint Preservation Check

| Constraint | Source | Status | Evidence |
|-----------|--------|--------|----------|
| <2s end-to-end feature-loop latency | `specs/00-DECISIONS.md` Decision 1 | PRESERVED | `02-ARCHITECTURE.md` §9.5 totals <600ms feature-to-UI, well inside 2s |
| MIT / open-source license | `specs/00-DECISIONS.md` Decision 3 | PRESERVED | No new license introduced; `01-REQUIREMENTS.md` Constraints "All computation is open-source (MIT/Apache 2/ISC)" |
| Open-source models only (librosa + audiocraft + essentia) | `specs/00-DECISIONS.md` Decision 4 | PRESERVED | Zero new ML models. All new code is librosa + numpy + scipy. `01-REQUIREMENTS.md` Constraints and `04-ROADMAP.md` §1 both explicitly state "No new ML models, no new production dependencies" |
| Store interface unchanged (write / get_latest / get_history / ping) | `CLAUDE.md` "Store Method Names" | PRESERVED | `02-ARCHITECTURE.md` §8 "Zero store schema change"; all four methods listed with "unchanged" annotations |
| V1 REST endpoint backward compatibility | `specs/02-ARCHITECTURE.md` §2.4 | PRESERVED | `02-ARCHITECTURE.md` §10(b) explicit contract; `GET /features/latest` and `GET /features/history` return FeatureVectors with 20 keys (additive) |
| V1 `build_prompt()` callable on new FeatureVector | `01-REQUIREMENTS.md` US-05 | PRESERVED | `02-ARCHITECTURE.md` §10(c); tested by `test_v1_prompt_callable_on_new_featurevector` in H1.S04 |
| FeatureVector 13 v1 keys intact, additive-only | `01-REQUIREMENTS.md` Constraints | PRESERVED | Tested by `test_v1_keys_preserved` in H1.S02 |
| FastAPI async loop not blocked by compute | `01-REQUIREMENTS.md` Constraints | PRESERVED | `02-ARCHITECTURE.md` §9.3 Layer 2 <5ms; generation loop stays in background thread; §7.4 places the event-loop call in <5ms budget |
| No Redis requirement | `CLAUDE.md` | PRESERVED | `02-ARCHITECTURE.md` §8: "The system remains runnable without Redis. The DictStore fallback must support Layer 2 via `get_history()` exactly as it does today." |
| Python 3.11+ only | `CLAUDE.md` | PRESERVED | No version changes |

**No constraints violated.**

---

## 7. Orphan Hunt

### 7.1 New files mentioned but not claimed by a slice

Cross-referenced every file named in `02-ARCHITECTURE.md` Module Map + `03-UI-SPEC.md` against `04-ROADMAP.md` slice work items.

| File (from Arch §2 or UI spec) | Claimed by slice? |
|--------------------------------|-------------------|
| `src/features/indicators.py` | YES — H1.S03 |
| `src/features/thresholds.py` | YES — H1.S02 |
| `src/generation/prompt_v2.py` | YES — H1.S04 |
| `tests/test_indicators.py` | YES — H1.S03 |
| `tests/test_prompt_v2.py` | YES — H1.S04 |
| `src/features/engine.py` modification | YES — H1.S02 |
| `src/generation/engine.py` modification | YES — H1.S05 |
| `src/api/app.py` modification (mic_loop + demo_start) | YES — H1.S06 |
| `ui/app.js` modification | YES — H1.S07 |
| `ui/index.html` modification | YES — H1.S07 (explicitly added in roadmap though not in arch §2 modified-files table — see G-13 below) |
| `ui/style.css` modification | YES — H1.S07 (explicitly added in roadmap though not in arch §2 modified-files table — see G-13 below) |
| `tests/test_features.py` modification | YES — H1.S02 |
| `tests/test_api.py` modification | YES — H1.S06 |
| `tests/test_generation.py` modification | YES — H1.S05 |
| `benchmarks/horizon-1-layer-1-latency.md` | YES — H1.S01 |
| `scripts/benchmark_layer1.py` | YES — H1.S01 |

**No orphan files.** One minor note (G-13 below): `02-ARCHITECTURE.md` §2 Modified Files table lists only `ui/app.js` but the roadmap H1.S07 also modifies `ui/index.html` and `ui/style.css`. The architecture is implicitly correct (the UI change needs HTML structure + styles) but the Module Map is incomplete.

### 7.2 Slice items referencing files not in the Module Map

Scanned all slice work items against `02-ARCHITECTURE.md` §2 (module map). All production-code files named in slices appear in the architecture map except:
- `ui/index.html` — mentioned in roadmap H1.S07 work items, missing from architecture §2. Minor omission.
- `ui/style.css` — same.

### 7.3 UI elements in spec with no backing data field

Cross-referenced `03-UI-SPEC.md` §3 elements against `02-ARCHITECTURE.md` §3.1 (new L1 keys) + §4.2 (indicator dict shape).

| UI element | Primary data source | Exists in schema? |
|-----------|--------------------|--------------------|
| BPM sparkline | `msg.data.bpm` (existing L1) | YES |
| Energy sparkline | `msg.data.rms_energy` (existing L1) | YES |
| Spectral direction arrow | `msg.indicators.spectral_trend` (L2) | YES — §4.2 indicator dict |
| Energy regime pill | `msg.indicators.energy_regime` (L2) | YES — §4.2 indicator dict |

**No phantom UI bindings.** All four UI elements trace back to schema fields.

### 7.4 Architecture components with no UI or slice

All architecture items covered. No dead code defined in architecture.

### G-13 (LOW) — Architecture §2 "Modified Files" table omits `ui/index.html` and `ui/style.css`

`02-ARCHITECTURE.md` §2 Modified Files table only lists `ui/app.js`. The roadmap H1.S07 correctly names all three UI files. Forge won't miss it because the roadmap is the work-item source of truth, but the architecture module map is stale.

Recommendation: Add two rows to `02-ARCHITECTURE.md` §2 Modified Files table: `ui/index.html` (add new DOM elements) and `ui/style.css` (pill/arrow/sparkline styles).

---

## 8. Non-Blocking Open Questions

Summary of open questions surfaced by downstream agents and my recommendation on each.

| Question | Raised By | Recommendation |
|----------|-----------|----------------|
| OQ-PLAN-01: `FLUX_NORM_DIVISOR` calibration from benchmark data | @planner | **DEFER to forge.** The benchmark script in H1.S01 is explicitly tasked with printing raw flux values; the divisor is tuned in H1.S08. Flow is well-defined. |
| OQ-PLAN-02: `spectral_contrast` range test assertion | @planner | **RESOLVE before forge.** Low-severity, but 10 seconds of spec editing saves a forge-time decision. Recommended: add `test_spectral_contrast_finite`. See G-08. |
| OQ-PLAN-03: `onset_regularity` behavior at N=10 | @planner | **DEFER to forge.** This is empirical calibration territory. H1.S08 play-testing is the right place to validate. |
| OQ-PLAN-04: Snapshot test string for `test_snapshot_full_trajectory` | @planner | **RESOLVE with one-line edit.** Add TDD note to H1.S04. See G-10. |
| OQ-UI-01: Sparkline canvas sizing in flex row | @ui-spec-writer | **DEFER to forge.** This is genuinely an implementation-time rendering call; the UI spec correctly does not prescribe pixel values. |
| OQ-UI-02: UI threshold values (hardcode vs fetch) | @ui-spec-writer | **RESOLVE before forge with a decision.** Two options in G-03. For a June 7 demo, hardcoding with a `// SYNC WITH` comment is acceptable and cheapest. |
| OQ-UI-03: Energy row flex layout with 5 elements | @ui-spec-writer | **DEFER to forge.** This is a rendering-at-resolution question. |
| Architecture §12 `chroma_entropy` semantics "worth confirming" | @architect | **RESOLVE before forge.** One-line spec edit. See G-09. |

**Total resolved-before-forge recommendations: 4 items, all cosmetic edits.** None block implementation.

---

## 9. Summary of Recommended Actions

Ordered by priority. All are small edits to existing documents; no spec is re-written.

1. **G-01 (HIGH) — `02-ARCHITECTURE.md` §6.5 and `04-ROADMAP.md` H1.S04:** Replace the "import `KEY_NAMES` and descriptor helpers" instruction with "inline-duplicate the three small descriptor functions and the `_KEY_NAMES` constant in `prompt_v2.py`." Avoids the `ImportError` on module-private names.

2. **G-02 (HIGH) — `02-ARCHITECTURE.md` §4.5 or §7.2:** Add a "Cold-start representations — two forms" paragraph explicitly stating the dict-form (inside-process) vs `None`-form (over-wire) asymmetry and confirming `build_prompt_v2` accepts both.

3. **G-03 (MEDIUM) — `03-UI-SPEC.md` OQ-UI-02:** Lock the decision. Hardcode the threshold in `app.js` with a `// SYNC WITH src/features/thresholds.py` comment. Mark OQ-UI-02 as RESOLVED.

4. **G-04 (MEDIUM) — `03-UI-SPEC.md` §2:** Reword the sparkline-buffer paragraph to say the buffer is fixed at 10 entries (not env-var-driven), matching the default `HORIZON1_WINDOW_N`.

5. **G-05 (MEDIUM) — `04-ROADMAP.md` H1.S06:** Elevate the `demo_start` broadcast update from "if it emits feature messages" to a first-class work item, and add `test_demo_start_broadcast_includes_indicators_field` to the test list.

6. **G-06 (MEDIUM) — `02-ARCHITECTURE.md` §7.4:** Remove "or in executor" hedging; lock the decision: `compute_indicators` is called directly on the asyncio event loop. Justify with the <5ms budget from §9.3.

7. **G-07 (MEDIUM) — `01-REQUIREMENTS.md` FR-01 mfcc row:** Change "coefficients 1-13" to "13 coefficients (0-12), zeroth coefficient is signal energy."

8. **G-12 (MEDIUM) — `03-UI-SPEC.md` §1:** Add one sentence clarifying that BPM trajectory visibility is satisfied by the sparkline's visible slope, not a separate directional arrow for BPM. Ties to AC-10.

9. **G-13 (LOW) — `02-ARCHITECTURE.md` §2 Modified Files table:** Add rows for `ui/index.html` and `ui/style.css`.

10. **G-08 (LOW) — `04-ROADMAP.md` H1.S02:** Add `test_spectral_contrast_finite` to the test list. Closes OQ-PLAN-02.

11. **G-09 (LOW) — `02-ARCHITECTURE.md` §12:** Replace the "worth confirming" chroma_entropy paragraph with a locked statement.

12. **G-10 (LOW) — `04-ROADMAP.md` H1.S04:** Add the snapshot-test TDD workflow note. Closes OQ-PLAN-04.

After these 12 edits, the bundle is ready to hand to forge.

---

## 10. Approval Checklist

### Requirements (01)
- [x] Reviewed by @spec-reviewer
- [x] All 10 acceptance criteria are testable and mapped to slices
- [x] Out-of-scope section is explicit and matches framework layer boundaries
- [x] All 7 OQ items resolved by TD decisions, verified in downstream docs
- [ ] FR-01 mfcc coefficient text to be corrected (G-07)

### Architecture (02)
- [x] Reviewed by @spec-reviewer
- [x] Schemas are well-typed (TypeScript WS frame, Python indicator dict)
- [x] Patterns preserve v1 contracts (store, REST, WS additivity, v1 prompt builder)
- [x] No scope creep into Layer 3 or 4
- [ ] §6.5 import-of-private-names to be resolved (G-01)
- [ ] §7.2 / §4.5 cold-start representation asymmetry to be clarified (G-02)
- [ ] §7.4 executor hedging to be locked (G-06)
- [ ] §12 chroma_entropy to be locked (G-09)
- [ ] §2 modified files table to include HTML+CSS (G-13)

### UI Spec (03)
- [x] Reviewed by @spec-reviewer
- [x] All four elements have complete binding + state + error specs
- [x] Accessibility (text + color) addressed
- [x] Component hierarchy matches existing DOM structure
- [ ] §1 BPM trajectory clarity for AC-10 (G-12)
- [ ] §2 sparkline buffer wording (G-04)
- [ ] OQ-UI-02 threshold source to be locked (G-03)

### Roadmap (04)
- [x] Reviewed by @spec-reviewer
- [x] Dependency chain is acyclic and justified
- [x] Each slice has done criteria and rollback plan
- [x] All 10 ACs have explicit slice coverage
- [x] Benchmark is gate (TD decision OQ-01)
- [ ] H1.S06 demo_start path to be first-class (G-05)
- [ ] H1.S04 TDD snapshot note to be added (G-10)
- [ ] H1.S02 spectral_contrast test to be added (G-08)
- [ ] H1.S04 KEY_NAMES import text to be aligned with G-01

### Overall
- [x] All open questions either TD-resolved, planner-flagged, or now resolvable in spec edits
- [x] All risks have mitigations
- [x] No constraints violated
- [ ] Apply 12 recommended edits from Section 9
- [ ] Human (Danny/Quincy) approves the fixed bundle
- [ ] Spec bundle then ready for forge

---

## 11. Risks Surfaced (Beyond Planner's List)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Forge agent imports `KEY_NAMES` literally and hits `ImportError` | High (the spec reads naturally, the symbol doesn't exist) | Low (10 min to diagnose) | G-01 fix |
| Forge agent misreads cold-start representation, breaks one of the two call sites | Medium | Medium (one of generation or UI fails silently on cold start) | G-02 fix |
| Server threshold calibration during play-testing silently drifts from UI threshold | Medium | Low (arrow direction contradicts prompt but does not crash) | G-03 fix |
| `demo/start` endpoint serves v1 payload (no indicators) after everything else is wired — caught only in manual demo | Medium | Medium (demo moment feels broken) | G-05 fix + explicit test |
| Benchmark says HPSS fits, but fine-tuning real music reveals 600ms spikes on polyphonic content | Medium | Medium (intermittent jank; still <2s total) | Already mitigated by H1.S08 post-implementation timing section |
| `spectral_contrast` unbounded high values shock the UI or prompt builder (neither consumes it in H1 — confirmed safe) | Low | Low | G-08 fix optional |

---

## 12. Assumptions Verified

| Assumption | Source | Verified |
|-----------|--------|----------|
| v1 `src/generation/prompt.py` has module-level descriptor helpers | Architecture §6 | FALSE — they are `_`-prefixed; drives G-01 |
| v1 `src/api/app.py` `mic_loop` runs `extract_features` via `run_in_executor` then broadcasts on the event loop | Architecture §7 | TRUE (confirmed by reading `src/api/app.py` lines 123-163) |
| v1 store interface has `write`, `get_latest(limit)`, `get_history(limit)`, `ping` | CLAUDE.md + architecture §8 | TRUE (documented in CLAUDE.md) |
| History ring capacity is 30; newest-first via `deque.appendleft` | Requirements §Constraints + architecture §4.1 | TRUE (spec-internal consistency) |
| `HORIZON1_WINDOW_N` default 10 is globally referenced | All four docs | TRUE |
| Demo hardware is RTX 5090 / 64GB | CLAUDE.md + requirements §AC-02 | TRUE |
| No new production dependencies | Requirements Constraints + roadmap §1 | TRUE (only librosa, numpy, scipy used) |

---

## 13. Status

**Verdict:** APPROVE-WITH-FIXES.

**Gap count:** 0 BLOCKER, 2 HIGH, 6 MEDIUM, 4 LOW = **12 total.**

**Top 3 by severity:**
1. G-01 `KEY_NAMES` import from `prompt.py` will `ImportError` (HIGH)
2. G-02 Cold-start representation dict-vs-null asymmetry undocumented (HIGH)
3. G-05 `demo/start` broadcast update under-specified with no test (MEDIUM)

**Next step:** Return to Quincy (TD) for approval of the 12 fixes, then dispatch each fix to the owning spec author (@requirements-analyst for G-07; @architect for G-01/02/06/09/13; @ui-spec-writer for G-03/04/12; @planner for G-05/08/10). After fixes are applied, the bundle is ready for forge.

---

*Review by: @spec-reviewer*
*Inputs: specs/horizon-1/01-REQUIREMENTS.md, 02-ARCHITECTURE.md, 03-UI-SPEC.md, 04-ROADMAP.md*
*Context: specs/00-DECISIONS.md, specs/02-ARCHITECTURE.md, specs/05-SONIC-ALPHA.md, CLAUDE.md, src/generation/prompt.py, src/api/app.py*

---

## Re-Review Pass (Fix Verification)

**Date:** 2026-04-16 (second pass)
**Scope:** Verification only. Does not re-run the full consistency matrix. Validates each of the 10 fixes targeted in the iteration (2 HIGH, 6 MEDIUM, 2 LOW) and checks that the 2 deferred LOWs remain acceptable and that no fix introduced a new gap.

### Fix Verification Table

| Gap | Sev | Expected Fix | Status | Evidence |
|-----|-----|-------------|--------|----------|
| G-01 | HIGH | `prompt_v2.py` inline-duplicates `_KEY_NAMES` + three descriptor helpers. NO import of private symbols from `prompt.py`. | CLOSED | `02-ARCHITECTURE.md` §6.5 line 550: "`prompt_v2.py` must NOT import these helpers from `src/generation/prompt.py` — the actual symbols are `_`-prefixed module-private names... Instead, inline-duplicate the four small helpers directly in `prompt_v2.py`... No import from `prompt.py` for these symbols." `04-ROADMAP.md` H1.S04 line 295: "Inline-duplicate `_KEY_NAMES` and the three descriptor helpers... into `src/generation/prompt_v2.py` as local private helpers; do not import the underscore-prefixed names from `prompt.py`". |
| G-02 | HIGH | Cold-start two-forms clarification in §4.5 or §7.2; `build_prompt_v2` accepts both dict form and None. | CLOSED | `02-ARCHITECTURE.md` §4.5 lines 391-396: "**Cold-start representations — two forms.** ... *In-process form* ... `{"available": False, ..., "warming_up_chunks_remaining": int}` ... *Wire form* ... `"indicators": null`... `build_prompt_v2(features, indicators)` ... must therefore accept EITHER (a) the dict form with `available=False`, OR (b) `None`... The guard at §6.3 (`if indicators is None or not indicators.get("available", False)`) already satisfies this." |
| G-03 | MED | UI hardcodes thresholds in `app.js` with `// SYNC WITH src/features/thresholds.py` comment; `/status` exposure out of scope. | CLOSED | `03-UI-SPEC.md` §3.3 line 185 ("Decision (resolves OQ-UI-02)") and §11 OQ-UI-02 lines 426-433 (marked RESOLVED with explicit `// SYNC WITH src/features/thresholds.py` literals). Section 10 line 416 lists "No serving of threshold values via `/status`... (OQ-UI-02 resolved: hardcoded in `app.js`)." |
| G-04 | MED | Sparkline buffer FIXED at 10 entries, does NOT track `HORIZON1_WINDOW_N`; mismatch acceptable. | CLOSED | `03-UI-SPEC.md` §2 line 66: "The sparkline buffer size is **fixed at 10 entries and does NOT track the server's `HORIZON1_WINDOW_N`**... If the server operates at a different N (via env override), the UI sparkline still shows the last 10 chunks received. This mismatch is acceptable for Horizon 1..." |
| G-05 | MED | First-class `demo/start` broadcast work item + `test_demo_start_broadcast_includes_indicators_field` added. | CLOSED | `04-ROADMAP.md` H1.S06 line 416 (first-class work item: "Apply the same indicator pattern to the `demo/start` endpoint broadcast... the `demo/start` endpoint is a critical demo surface (S11 DONE per CLAUDE.md) and must not be left on the v1 payload shape") and line 420 (new test `test_demo_start_broadcast_includes_indicators_field`). |
| G-06 | MED | `compute_indicators` called directly on asyncio event loop. No executor hedge. | CLOSED | `02-ARCHITECTURE.md` §7.4 line 660: "`compute_indicators` is called directly on the asyncio event loop — not in `run_in_executor`. This is the locked decision: §9.3 shows Layer 2 computation is < 5ms on a 10-entry history... Wrapping it in `run_in_executor` would add thread-pool overhead with no benefit." No residual "or" language. |
| G-07 | MED | `mfcc` row reads "13 coefficients (indexed 0-12); zeroth coefficient is signal energy and is retained." | CLOSED | `01-REQUIREMENTS.md` FR-01 table line 62: "Mean over time; 13 coefficients (indexed 0-12); the zeroth coefficient represents signal energy and is retained." AC-01 line 146 also updated: "coefficients indexed 0-12, zeroth coefficient is signal energy." |
| G-08 | LOW | `test_spectral_contrast_finite` added. OQ-PLAN-02 RESOLVED. | CLOSED | `04-ROADMAP.md` H1.S02 line 175 (test added: "asserts all values in the `spectral_contrast` list are finite floats (no NaN/Inf) across silent, sine, and noise fixtures; closes OQ-PLAN-02"). §10 OQ-PLAN-02 line 696 explicitly marked "**RESOLVED**". |
| G-09 | LOW | `chroma_entropy` point-in-time locked; `chroma_volatility` is window-based dual. No hedging. | CLOSED | `02-ARCHITECTURE.md` §12 lines 847, 858: "None — all design decisions resolved." ... "`chroma_entropy` is computed from the current chunk's 12-element chroma vector (point-in-time Shannon entropy), per specs/05-SONIC-ALPHA.md L99. `chroma_volatility` is the window-based dual that operates over the history ring. These are intentionally distinct indicators." Also repeated in §4.4 line 322 as a locked statement. No "worth confirming" language remains. |
| G-10 | LOW | TDD capture-after-impl snapshot workflow documented. OQ-PLAN-04 RESOLVED. | CLOSED | `04-ROADMAP.md` H1.S04 line 313: "TDD note: stub `expected=""` initially, implement `build_prompt_v2`, run to capture actual output, assert stability, then commit the captured snapshot (capture-after-impl workflow — closes OQ-PLAN-04)." §10 OQ-PLAN-04 line 702 marked "**RESOLVED**". |
| G-12 | MED | BPM trajectory visibility satisfied by sparkline slope alone; AC-10 explicitly cited. | CLOSED | `03-UI-SPEC.md` §1 line 21: "**AC-10 (BPM trajectory visibility):** The requirement that BPM trajectory be visible in the UI (AC-10 in 01-REQUIREMENTS.md) is satisfied by the BPM sparkline's visible slope. No separate BPM direction arrow is needed or added." Reinforced in §3.1 line 98. |
| OQ-01..07 | — | All 7 requirements-level open questions marked RESOLVED with TD decisions recorded. | CLOSED | `01-REQUIREMENTS.md` §"Open Questions (Resolved)" lines 262-310. Each of OQ-01 through OQ-07 has a **RESOLVED** block with the TD decision. Header says "All seven open questions were resolved by the Technical Director before architecture began." Document status is "APPROVED — all open questions resolved by Technical Director." |

### Deliberately Deferred LOW Gaps (Non-Blocking)

The fix iteration left 2 LOW gaps open by design. Both were judged acceptable for forge handoff; restated here so they are not lost:

- **G-11** — Intentional no-gap slot. Reserved placeholder in the table; nothing to fix. Rationale: reserved numbering for later pass.
- **G-13** — `02-ARCHITECTURE.md` §2 Modified Files table omits `ui/index.html` and `ui/style.css`. Rationale: the roadmap H1.S07 work items are the operative source of truth for forge — it lists all three UI files explicitly. The architecture module map is cosmetically stale but not functionally misleading; no forge execution risk.

### New Gaps Introduced by the Fix Iteration

None. All 10 targeted fixes are additive tightening. Specifically reviewed for:
- No new imports or symbols referenced that don't exist
- No new cross-doc inconsistencies (threshold literals in UI spec §3.3 still match architecture §5; window clamping rules unchanged; WS payload shape unchanged)
- No requirement-to-slice coverage regressions (traceability in roadmap §7 still covers AC-01 through AC-10)

One minor observation (not a gap): `02-ARCHITECTURE.md` §4.5 line 393 mentions `"warming_up_chunks_remaining": int` as part of the in-process dict form, but §4.2 return-shape block and §4.5 `_cold_start_result()` implementation do NOT include that key. This is a cosmetic drift in the prose ("fully-keyed dict where `available` is `False` and all indicator keys are `None`" followed by a non-existent extra key). Implementation will follow §4.2 / `_cold_start_result()`. Flag as editorial note, not a gap — the guard logic in `build_prompt_v2` and the UI handler never read this key, so no forge-time impact.

### New Verdict

**APPROVE.** Ready for implementation handoff.

All 2 HIGH gaps are CLOSED. All 6 MEDIUM gaps are CLOSED. Both targeted LOW gaps (G-08, G-10) are CLOSED. All 7 requirements-level OQs are marked RESOLVED with TD decisions recorded. The 2 deferred items (G-11 reserved slot, G-13 architecture module-map cosmetic) do not block forge because the roadmap work items carry the operative file list.

### Final Recommendation

Proceed to forge (H1.S01 benchmark first). The 12-edit gap list from the original review is substantively closed. No second fix iteration required.

---

*Re-review by: @spec-reviewer (second pass)*
*Verification scope: G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08, G-09, G-10, G-12 plus OQ-01..OQ-07 requirements-level resolution*

---

## Re-Review Pass 2 (Frank's Conditions)

**Date:** 2026-04-16 (third pass)
**Scope:** Verification of Frank's three QC conditions after second-pass APPROVE:
1. Demo warm-up gap — `/demo/start` must iterate all chunks per file (not `next(chunks)`)
2. `warming_up_chunks_remaining` prose-vs-code drift — prose reference must be removed
3. `FLUX_NORM_DIVISOR` test-ordering trap — H1.S01 must emit raw flux p95 and recommend divisor; H1.S02 must calibrate divisor BEFORE committing `test_spectral_flux_range`

### Condition Check Table

| Check | Status | Evidence |
|-------|--------|----------|
| **FIX 1a** — `02-ARCHITECTURE.md` §2 Modified Files table for `src/api/app.py` names BOTH `mic_loop` AND `demo_start`, and explicitly says `demo_start` iterates all chunks | CLOSED | `02-ARCHITECTURE.md` §2 line 33: "Modify both `mic_loop` AND the `demo_start` endpoint. In `mic_loop`: extend the broadcast call to compute and include indicators... In `demo_start`: additionally changed to iterate all chunks (not just `next(chunks)`) so history accumulates to ≥N across each multi-chunk file." |
| **FIX 1b** — `02-ARCHITECTURE.md` §7.4.1 documents: current `next(chunks)` behavior, new full-generator iteration, chunk-level `asyncio.sleep(0.1)` within a file, file-level `asyncio.sleep(0.5)` between files, additive `chunks_processed` integer in response body | PARTIAL | `02-ARCHITECTURE.md` §7.4.1 lines 664-676 exist and cover: current-behavior description ("`next(chunks)` is called... taking only the first 2-second slice... Layer 2 indicators remain `null` throughout the entire demo"); new behavior intent ("Iterate the full generator from `load_and_chunk(str(wav_path))`"); chunk-level and file-level sleep rationale ("The 0.1s sleep between chunks within a file... The 0.5s inter-file gap is preserved"); and the additive `chunks_processed: int` response body field. **However**, line 670 ("**New behavior (v2):** Iterate the full generator from `load_and_chunk(str(wav_path))` for each WAV file. For each chunk:") is followed by two blank lines where the per-chunk step list appears to have been truncated. The concrete per-chunk pseudocode exists in `04-ROADMAP.md` H1.S06 line 419 (full three-line indicator pattern + broadcast). Forge has the operative step list in the roadmap; the architecture prose has an orphan "For each chunk:" fragment. Minor editorial defect; not a forge blocker. |
| **FIX 1c** — `02-ARCHITECTURE.md` §10(d) backward-compat contract notes the `/demo/start` visible behavior change: more broadcast frames per request, additive response body field, no breaking change | CLOSED | `02-ARCHITECTURE.md` §10(d) line 790: "The `demo_start` endpoint's visible behavior also changes: it now emits one broadcast frame per 2-second chunk (across all chunks in each file) rather than one frame per file. The `/demo/start` response body's `files_processed` count and `results` array shape are unchanged (one result entry per file); a `"chunks_processed": int` field is added to each per-file result entry. This is an additive response body change; no breaking change to `/demo/start` consumers." |
| **FIX 1d** — `04-ROADMAP.md` H1.S06 Work Items contain the expanded demo/start bullet (full iteration, per-chunk indicators, 0.1s/0.5s pacing, `chunks_processed`) | CLOSED | `04-ROADMAP.md` H1.S06 line 419: "Modify the `demo/start` endpoint to iterate ALL chunks per file (replacing `first_chunk = next(chunks)`). For each WAV file: iterate the generator returned by `load_and_chunk(str(wav_path))`; for each chunk call `extract_features(chunk, source="file")`, `store.write(features)`, the three-line indicator computation pattern... and `await manager.broadcast({"type": "features", "data": features, "indicators": ind_payload})`. Sleep `await asyncio.sleep(0.1)` between chunks within a file (chunk-level pacing) and `await asyncio.sleep(0.5)` between files (file-level pacing). Add a `chunks_processed` integer field to each per-file result entry in the response body." |
| **FIX 1e** — `test_demo_start_broadcast_includes_indicators_field` asserts BOTH null (early frames) AND populated (late frames after history reaches N) | CLOSED | `04-ROADMAP.md` H1.S06 line 423: "Assert that the sequence of broadcast frames emitted by the `POST /demo/start` endpoint contains the `"indicators"` field throughout. Capture the full frame sequence and verify: (i) broadcast frames emitted early in the request (history < N) carry `indicators: null`, AND (ii) broadcast frames emitted late in the request (history >= N) carry a populated indicators dict. The test must assert both sides of this null→populated transition..." |
| **FIX 1f** — New test `test_demo_start_response_includes_chunks_processed` exists in H1.S06's test list | CLOSED | `04-ROADMAP.md` H1.S06 line 424: "`test_demo_start_response_includes_chunks_processed`: Assert the response body's `results` array contains `chunks_processed` as an integer per file entry. If the file is the standard 10-second demo fixture at 2-second chunks, `chunks_processed` should be 5." |
| **FIX 1g** — Section 6 Risk Table has a stronger row for the full-chunk-iteration failure mode | CLOSED | `04-ROADMAP.md` §6 line 616: "`demo/start` endpoint fails to exercise trajectory features because it processes one chunk per file | Low (now mitigated by explicit work item requiring full chunk iteration) | High (demo appears broken at hackathon — indicators never populate in demo mode) | H1.S06 | Iterate all chunks via `load_and_chunk` generator. `test_demo_start_broadcast_includes_indicators_field` asserts the null→populated transition across the emitted frame sequence." Explicit, specific, names the mitigating test. |
| **FIX 2a** — `warming_up_chunks_remaining` NOT mentioned anywhere in `02-ARCHITECTURE.md` | CLOSED | `grep warming_up_chunks_remaining specs/horizon-1/02-ARCHITECTURE.md` returns ZERO matches. The only occurrences in `specs/horizon-1/` are inside `05-REVIEW.md` itself (lines 445, 471 — pre-existing review text quoting the old state). The architecture doc is clean. |
| **FIX 2b** — §4.5 in-process form list reads exactly `{"available": False, "delta_bpm": None, ..., "onset_regularity": None}` with no extra keys | CLOSED | `02-ARCHITECTURE.md` §4.5 line 393: "*In-process form* (inside `compute_indicators`, `GenerationEngine`, and direct callers): `{"available": False, "delta_bpm": None, ..., "onset_regularity": None}` — a fully-keyed dict where `available` is `False` and all indicator keys are `None`. This is what `compute_indicators()` always returns; it is never `None`." No `warming_up_chunks_remaining` or any other extra key in the prose list. Matches `_cold_start_result()` in lines 373-387 exactly. |
| **FIX 3a** — `04-ROADMAP.md` H1.S01 Work Items require raw (pre-normalization) spectral_flux per fixture to be computed, printed, and written to the benchmark report | CLOSED | `04-ROADMAP.md` H1.S01 line 103: "For `spectral_flux`, compute the raw (pre-normalization) value for each fixture: `np.sum(np.diff(np.abs(librosa.stft(audio)), axis=1) ** 2, axis=0).mean()`. Print per-fixture raw flux and its p95 across all 30 timed runs. Include these raw flux statistics in the `benchmarks/horizon-1-layer-1-latency.md` report in a dedicated 'Raw Spectral Flux Calibration' section." |
| **FIX 3b** — H1.S01 Work Items require a recommended `FLUX_NORM_DIVISOR` value in the benchmark report | CLOSED | `04-ROADMAP.md` H1.S01 line 104: "Recommend a `FLUX_NORM_DIVISOR` value in the benchmark report based on the fixtures' raw flux p95. Rule: set `FLUX_NORM_DIVISOR` to roughly the p95 of raw flux across music-like fixtures (chirp, sine) so that typical music flux maps to ~[0.3, 0.95] and silence maps to ~0. Explicitly document the recommended numeric value in the report." |
| **FIX 3c** — H1.S02 Preconditions include HALT-style precondition requiring H1.S01's report to contain the recommended divisor value BEFORE H1.S02 begins | CLOSED | `04-ROADMAP.md` H1.S02 line 147: "H1.S01 complete AND benchmark report contains a recommended `FLUX_NORM_DIVISOR` value. Before writing Layer 1 feature tests in this slice, update `src/features/thresholds.py`'s `FLUX_NORM_DIVISOR` from the placeholder `1.0` to the recommended value from the benchmark report. If the benchmark report's recommended value is not present, HALT H1.S02 and return to H1.S01." Explicit HALT phrasing. |
| **FIX 3d** — H1.S02 Work Items reference the benchmark-derived divisor value rather than the `1.0` placeholder | CLOSED | `04-ROADMAP.md` H1.S02 line 161: "`FLUX_NORM_DIVISOR = <benchmark-derived p95 from H1.S01 report>` (must be set before `test_spectral_flux_range` is committed; placeholder value removed in this slice)". The placeholder is explicitly superseded by the benchmark-derived value before the range test is committed. |
| **FIX 3e** — §10 OQ-PLAN-01 marked RESOLVED with the test-ordering trap explicitly closed | CLOSED | `04-ROADMAP.md` §10 line 696: "**OQ-PLAN-01: RESOLVED** — H1.S01 benchmark emits raw flux p95 and recommends a `FLUX_NORM_DIVISOR` value in a dedicated 'Raw Spectral Flux Calibration' section. H1.S02 Preconditions require `FLUX_NORM_DIVISOR` to be set to that benchmark-recommended value before writing `test_spectral_flux_range`. The test-ordering trap (divisor=1.0 makes range test trivially pass while real music clips to 1.0) is closed." The trap is named explicitly and the closure mechanism is documented. |

### New Gaps Introduced by This Fix Pass

One editorial defect, not a blocker:

- **02-ARCHITECTURE.md §7.4.1 line 669-671** has "**New behavior (v2):** Iterate the full generator from `load_and_chunk(str(wav_path))` for each WAV file. For each chunk:" followed by two blank lines where the per-chunk step list appears to have been truncated during the fix pass. The surrounding prose (chunk-level sleep rationale, file-level sleep rationale, response body section) is intact and correct. The concrete per-chunk pseudocode lives in `04-ROADMAP.md` H1.S06 line 419, which is the operative source of truth for forge. Forge will not be blocked; the architecture reads slightly choppy. Editorial recommendation (post-handoff): either delete the orphan "For each chunk:" sentence or replace it with a short inline list (e.g., "call `extract_features` → `store.write` → compute indicators → `broadcast` → `asyncio.sleep(0.1)`").

### Known-Unknown Items Restated for Forge

Frank flagged two items as "known-unknown, not blocking." Restated here so they do not get lost in handoff:

1. **`onset_regularity` semantics at N=10** (OQ-PLAN-03 in `04-ROADMAP.md` §10 line 700). With a 10-chunk × 2-second window (~20s of audio), autocorrelation peak search at "lag 1 or 2" may not be musically meaningful — the beat period at 120 BPM is ~0.5s which is 4 chunks. Calibration territory. Verify during H1.S08 play-testing; if consistently near-zero for periodic music, widen the lag search to lags 2–5. Not a spec gap.

2. **v1 `print()` noise in `scripts/benchmark_layer1.py`**. The H1.S01 benchmark script uses `print()` for per-feature timing output. No structured logging. Acceptable for a one-off benchmark script that writes to both stdout and a markdown artifact; not worth upgrading to `logging` for Horizon 1. Forge should preserve the `print()`-to-markdown pattern.

### New Verdict

**APPROVE.** Ready for forge handoff.

All three of Frank's conditions are CLOSED. The single editorial defect in §7.4.1 (orphan "For each chunk:" fragment) is cosmetic and does not impair forge execution because the concrete per-chunk pseudocode is fully specified in `04-ROADMAP.md` H1.S06. No new gaps introduced. Both known-unknown items (`onset_regularity` calibration, benchmark script `print()` noise) remain out-of-scope for Horizon 1 and on the table for post-implementation tuning.

### Final Recommendation

Proceed to forge. Begin with H1.S01 (Latency Benchmark) — the gate slice. The benchmark report will produce both the HPSS verdict and the `FLUX_NORM_DIVISOR` value required by H1.S02's HALT-style precondition. All three of Frank's structural concerns (demo warm-up, prose-vs-code drift, test-ordering trap) are closed at the spec level. One optional cleanup pass on §7.4.1 orphan fragment may be done inline during forge if the implementing agent notices it.

---

*Re-review Pass 2 by: @spec-reviewer*
*Verification scope: Frank's three conditions (demo/start full-chunk iteration, `warming_up_chunks_remaining` removal, FLUX_NORM_DIVISOR test-ordering gate)*
