# SonicStore — Progress Tracker
**Last updated:** 2026-04-17
**Updated by:** Quincy (Technical Director)

---

## Current State

**v1 + Horizon 1 shipped.** All 11 v1 slices + all 8 Horizon 1 slices COMPLETE.
**Tests:** **111 passing** (68 v1 baseline + 43 new Horizon 1). 3 Redis integration deselected.
**FeatureVector schema:** 20 keys (13 v1 + 7 Layer 1 widening).
**Latest commit:** `32ce86f` — "Implement Horizon 1: Layer 1 widening + Layer 2 temporal indicators"

## Slice Status

| Slice | Name | Status | Tests |
|-------|------|--------|-------|
| S01 | Project Scaffolding | DONE | manual + 3 fixtures |
| S02 | Feature Engine | DONE | 14 passing |
| S03 | Prompt Builder | DONE | 20 passing |
| S04 | Store Layer | DONE | 12 unit + 3 integration |
| S05 | REST API | DONE | 9 passing |
| S06 | WebSocket Server | DONE | 4 passing |
| S07 | Web UI | DONE | manual |
| S08 | Mic Ingestion | DONE | manual (scripts/test_mic_capture.py) |
| S09 | Mic Loop | DONE | manual |
| S10 | Generation Engine | DONE | 6 passing (mocked) |
| S11 | Polish + Demo Mode | DONE | manual |

## Horizon 1 Slice Status

| Slice | Name | Status | Tests |
|-------|------|--------|-------|
| H1.S01 | Latency Benchmark | DONE | artifact (benchmarks/horizon-1-layer-1-latency.md) |
| H1.S02 | Layer 1 Widening + Thresholds | DONE | 12 passing |
| H1.S03 | Layer 2 Indicators Module | DONE | 16 passing |
| H1.S04 | Prompt Builder v2 | DONE | 13 passing |
| H1.S05 | GenerationEngine Wiring | DONE | 2 passing |
| H1.S06 | WS Payload + demo_start iterate | DONE | 3 passing |
| H1.S07 | Web UI Indicator Elements | DONE | manual (rehearsal) |
| H1.S08 | Polish + Integration Verification | DONE | REST E2E verified |

Benchmark verdict: **PASS** — combined p95 339.91ms / 500ms budget. `FLUX_NORM_DIVISOR` calibrated to 203820.109375.

## Specs Written

| Spec | Status | Purpose |
|------|--------|---------|
| 00-DECISIONS.md | LOCKED | 4 architectural constraints |
| 00-INTAKE.md | COMPLETE | Project intake / problem definition |
| 02-ARCHITECTURE.md | APPROVED | System architecture, component design, interfaces |
| 03-ROADMAP.md | COMPLETE | 11 implementation slices with Done When criteria |
| 04-HORIZONS.md | DRAFT | Three horizons: derivative, learned, interaction features |
| 05-SONIC-ALPHA.md | DRAFT | 4-layer feature intelligence framework (the mental model) |
| horizon-1/ (5 docs) | COMPLETE | Horizon 1 spec bundle: requirements, architecture, UI spec, roadmap, review |

## What's Next

### Immediate — Next session (Horizon 1 dogfood)
- **Dogfood Horizon 1 on RTX 5090 demo hardware** — re-run `scripts/benchmark_layer1.py`, play-test on real music, observe indicator behavior live
- **Drop demo WAVs** into `demo/` directory (currently only README.txt) — need ≥10s files for indicator warm-up
- Validate `onset_regularity` semantics empirically at N=10
- Install audiocraft on ROG Strix SCAR 18 (still pending from v1)
- Run `make redis-up && pytest tests/ -v` — verify Redis integration tests
- Pre-cache MusicGen model (~600MB to ~/.cache/huggingface)
- Run full demo 10 times, tune `GENERATION_INTERVAL` + thresholds
- Record 30-second fallback video
- Git tag v1.1.0-horizon-1

### Post-rehearsal (Horizon 2)
- Spec learned features: representation learning on audio chunks
- Spec session logging infrastructure (paired feature+generation data)
- Offline training pipeline for the interaction dataset

## Known Constraints

- Dev machine: headless Linux VM, no GPU, no PortAudio — mic import is lazy, audiocraft not installed
- Demo machine: ASUS ROG Strix SCAR 18 (RTX 5090, 64GB RAM) — real testing happens there
- audiocraft not installed on dev machine — generation tests are mocked, real inference untested until ROG Strix

## Session Log

| Date | Session | Work Done |
|------|---------|-----------|
| 2026-04-16 | Initial build | Decisions locked, architecture + roadmap, S01-S04, spec review |
| 2026-04-16 | API through Mic | S05-S09 implemented, 51 tests |
| 2026-04-16 | S10-S11 + QC | S10-S11 implemented, Frank QC audit, spec remediation (S01-S05 gaps closed), Sonic Alpha framework. 68 tests. README. |
| 2026-04-17 | Horizon 1 shipped | Full spec → forge cycle: 5-doc bundle, 8 slices, 2 spec-review passes + 2 Frank QC passes. 111 tests. Demo warm-up + FLUX_NORM_DIVISOR sequencing + executor wrap closed. Commit `32ce86f`. |
