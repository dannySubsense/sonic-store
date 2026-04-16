# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SonicStore is a real-time MIR (Music Information Retrieval) feature extraction service with an AI music generation feedback loop. Built for a hackathon (June 6-7, 2026). The demo flow: live audio in -> extract features -> display visually -> condition a MusicGen prompt -> generate complementary audio -> play back.

## Commands

```bash
make install          # Install production deps
make test             # Run all tests: pytest tests/ -v
make run              # Start server: uvicorn src.api.app:app --reload --port 8000
make redis-up         # Start Redis (optional — DictStore fallback exists)

# Run a single test file
pytest tests/test_features.py -v

# Run a single test
pytest tests/test_features.py::test_chroma_shape_and_range -v

# Skip Redis-dependent tests
pytest tests/ -v -m "not integration"

# Generate test audio fixtures (required before first test run)
python3 scripts/generate_test_audio.py
```

Python 3.11+ required (audiocraft compatibility). Use `python3` not `python` on this system.

## Locked Decisions (Do Not Revisit)

These are in `specs/00-DECISIONS.md` and are constraints, not open questions:

1. **Latency:** <2s for v1. No <50ms real-time tier.
2. **Product identity:** Feature Store + Feedback Loop. Agentic Prosthetic is north star only.
3. **License:** MIT, open source.
4. **Models:** Open-source only (librosa, audiocraft, essentia). No partnerships yet.

## Architecture

Full spec: `specs/02-ARCHITECTURE.md`. Key data flow:

```
Mic/File -> AudioIngestion -> FeatureEngine -> HotStore -> FeatureAPI -> WebSocket -> WebUI
                                                   |
                                          GenerationEngine (background thread)
                                                   |
                                     PromptBuilder -> MusicGen-Small -> audio_b64 -> WebUI
```

**Store pattern:** `AbstractStore` protocol (`src/store/base.py`) with two implementations. `DictStore` (in-memory, thread-safe with `threading.Lock`) is the default. `RedisStore` (pipeline writes, TTL=60s) activates if Redis is available. Selection happens at startup — Redis is never required.

**Generation is non-blocking:** `GenerationEngine` runs in a `threading.Thread`, never in the FastAPI async loop. Output flows via `queue.Queue`. PyTorch inference is not async-safe.

**MusicGen device selection:** CUDA -> FP16; MPS -> FP32 (audiocraft MPS is unstable with FP16); CPU -> FP32 fallback.

**Audio contract:** All internal audio is `np.ndarray` float32, shape `(44100,)` (2 seconds at sr=22050), values in `[-1.0, 1.0]`.

## Implementation Status

Roadmap: `specs/03-ROADMAP.md`. Slices are ordered by dependency.

| Slice | Status | Key Files |
|-------|--------|-----------|
| S01 Scaffolding | DONE | requirements.txt, Makefile |
| S02 Feature Engine | DONE | src/features/engine.py, key_detection.py |
| S03 Prompt Builder | DONE | src/generation/prompt.py |
| S04 Store Layer | DONE | src/store/dict_store.py, redis_store.py |
| S05 REST API | DONE | src/api/routes_analyze.py, routes_features.py |
| S06 WebSocket | DONE | src/api/websocket.py, app.py |
| S07 Web UI | DONE | ui/ directory |
| S08 Mic Ingestion | DONE | src/ingestion/mic.py |
| S09 Mic Loop | DONE | wires S06+S08 in app.py |
| S10 Generation Engine | STUB | src/generation/engine.py |
| S11 Polish | NOT STARTED | error handling, demo mode |

"DONE" = fully implemented with passing tests. "STUB" = correct signatures and imports, body raises `NotImplementedError`.

## Store Method Names

The actual interface methods (matching the code, not all spec docs):
- `store.write(feature_vector)` — persist latest + append to history
- `store.get_latest()` -> `dict | None`
- `store.get_history(limit=30)` -> `list[dict]`
- `store.ping()` -> `bool`

## Test Fixtures

Tests generate synthetic audio inline via `make_sine()` helper (440Hz sine wave as numpy array). No external audio files required for `make test`. The script `scripts/generate_test_audio.py` creates WAV files for manual testing.

## FeatureVector Schema

The `extract_features()` return dict (see `src/features/engine.py`) contains 13 keys: `timestamp`, `chunk_index`, `source`, `duration_seconds`, `chroma` (12-element list), `bpm`, `key_pitch_class` (0-11), `key_mode` ("major"/"minor"), `rms_energy` (0-1), `spectral_centroid_hz`, `onset_strength` (0-1), `mel_spectrogram` (128xT nested list), `waveform_display` (2048-element list).

## Research Corpus

`research/` contains ~28 completed research documents. The research phase is done — do not add more research docs. Start from the specs, not the research. The key synthesis is `research/00-SYNTHESIS.md` if background context is needed.
