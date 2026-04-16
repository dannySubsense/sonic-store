# SonicStore

**Real-time music intelligence with an AI feedback loop.**

SonicStore listens to live audio, extracts musical features in real time, visualizes them, and generates complementary music using AI — creating a live conversation between human and machine.

```
    ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌─────────┐
    │  YOU    │────▶│ FEATURE  │────▶│   HOT     │────▶│  WEB    │
    │  PLAY   │     │ ENGINE   │     │  STORE    │     │   UI    │
    └─────────┘     └──────────┘     └─────┬─────┘     └─────────┘
         ▲               │                 │                │
         │               │           ┌─────▼─────┐         │
         │               │           │ GENERATION │         │
         │               │           │  ENGINE    │         │
         │               │           │ (MusicGen) │         │
         │               │           └─────┬─────┘         │
         │               │                 │                │
         └───────────────┴────── YOU HEAR ◀┴────────────────┘
```

You play. SonicStore analyzes. The AI responds. You respond to the AI. The loop continues.

---

## What It Extracts

Every second, SonicStore computes from your live audio:

| Feature | What It Tells You |
|---------|------------------|
| **Chroma** | Which of the 12 pitch classes are present (C, C#, D, ... B) |
| **BPM** | Tempo — how fast you're playing |
| **Key** | Tonal center — D minor, A major, etc. (Krumhansl-Schmuckler algorithm) |
| **RMS Energy** | How loud / how much intensity |
| **Spectral Centroid** | Brightness — bass-heavy vs. airy |
| **Onset Strength** | Rhythmic attack intensity |

These features flow into the AI generation engine, which builds a natural language prompt and generates a 10-second complementary audio clip via **MusicGen-Small**.

Example prompt (generated automatically from your playing):
> *"energetic, driving balanced musical accompaniment, upbeat, 124 BPM, D minor, complementary to the input melody, instrumental"*

---

## What You See

```
┌───────────────────────────────────────────────────────────┐
│  SonicStore                      [Start] [Stop] [Demo]    │
├────────────────┬──────────────────────────────────────────┤
│  WAVEFORM      │  BPM: 124          Key: D minor          │
│  ╱╲╱╲╱╲╱╲╱╲   │  Energy: ████░░░░  Spectral: 2300 Hz     │
│                │  Onset: 0.31                              │
├────────────────┴──────────────────────────────────────────┤
│  CHROMA HEATMAP                                            │
│  B  ░░▓▓░░░░░░░░░░░░░░░░                                  │
│  A  ░░░░░░▓▓▓▓░░░░░░░░░░   ← scrolling time →            │
│  G  ░░░░░░░░░░▓▓░░░░░░░░                                  │
│  ...                                                       │
│  C  ░░░░░░░░░░░░░░░░░░░░                                  │
├────────────────────────────────────────────────────────────┤
│  AI: "energetic, driving balanced accompaniment, 124 BPM"  │
│  [Play Generated Clip]                  Generated in 3.2s  │
└────────────────────────────────────────────────────────────┘
```

Dark theme. Canvas rendering. No frameworks. Updates at ~1Hz from live mic input.

---

## Architecture

```
src/
├── ingestion/
│   ├── mic.py              # sounddevice → ring buffer → overlapping chunks
│   └── file.py             # librosa file load → chunk generator
├── features/
│   ├── engine.py           # extract_features() → FeatureVector dict
│   └── key_detection.py    # Krumhansl-Schmuckler key profiles
├── store/
│   ├── base.py             # AbstractStore protocol
│   ├── dict_store.py       # In-memory (default, thread-safe)
│   └── redis_store.py      # Redis with pipeline writes (optional)
├── generation/
│   ├── engine.py           # Background thread: poll → prompt → MusicGen → base64 WAV
│   └── prompt.py           # Feature-to-text prompt mapping
└── api/
    ├── app.py              # FastAPI: lifespan, WebSocket, /status, /demo/start
    ├── websocket.py         # ConnectionManager: broadcast to all clients
    ├── routes_analyze.py    # POST /analyze (file upload)
    └── routes_features.py   # GET /features/latest, /features/history

ui/
├── index.html              # Single page, no build step
├── app.js                  # WebSocket client, Canvas rendering, AudioContext
└── style.css               # Dark theme, monospace
```

**Key design decisions:**
- Generation runs in a **background thread** (PyTorch is not async-safe), communicates via `queue.Queue`
- MusicGen loads **lazily** — server starts immediately, model loads in background
- Redis is **optional** — DictStore fallback is seamless
- **No external dependencies at runtime** — everything runs locally, no cloud, no API keys

---

## The Feedback Loop

```
                    ┌──────────────────┐
                    │                  │
          ┌────────▼────────┐         │
          │   Mic Capture   │         │
          │  (2s chunks,    │         │
          │   1s hop,       │         │
          │   50% overlap)  │         │
          └────────┬────────┘         │
                   │                  │
          ┌────────▼────────┐         │
          │    Feature      │         │
          │   Extraction    │         │     THE
          │  (6 features,   │         │     LOOP
          │   <500ms)       │         │
          └────────┬────────┘         │
                   │                  │
          ┌────────▼────────┐         │
          │  Store + Stream │         │
          │  (WebSocket to  │         │
          │   browser UI)   │         │
          └────────┬────────┘         │
                   │                  │
          ┌────────▼────────┐         │
          │   MusicGen      │         │
          │  Generation     │         │
          │  (10s clip,     │         │
          │   ~3s on GPU)   │         │
          └────────┬────────┘         │
                   │                  │
          ┌────────▼────────┐         │
          │  Audio Playback │         │
          │  (browser       │         │
          │   AudioContext)  │─────────┘
          └─────────────────┘
            musician hears AI
            and responds...
```

Total loop latency: **~6-8 seconds** (mic capture + extraction + generation interval + MusicGen inference + playback).

---

## Quick Start

```bash
# Prerequisites: Python 3.11+, pip

# Install
git clone https://github.com/dannySubsense/sonic-store.git
cd sonic-store
make install          # or: pip install -r requirements.txt

# Generate test fixtures
python3 scripts/generate_test_audio.py

# Run tests (68 tests, no GPU needed)
make test

# Start the server
make run              # uvicorn on http://localhost:8000

# Open the UI
open http://localhost:8000/ui
```

### With a microphone
1. Open `http://localhost:8000/ui`
2. Click **Start** — grant mic permission
3. Play or sing — watch features update live
4. Wait ~6s — AI generates a response, click **Play**

### Without a microphone (demo mode)
1. Place WAV files in the `demo/` directory
2. Click **Demo** in the UI — or `POST /demo/start`
3. Features cycle through each file with 0.5s spacing

### API endpoints
```
POST /analyze              Upload a WAV, get FeatureVector JSON
GET  /features/latest      Most recent FeatureVector
GET  /features/history     Last 30 FeatureVectors (newest first)
GET  /status               System status (model loaded, mic state, etc.)
POST /demo/start           Run demo mode from demo/ directory
WS   /ws/features          Real-time feature + generation streaming
```

---

## What's Next: Sonic Alpha

SonicStore v1 extracts features that describe what the audio **is** — right now, this instant. That's Layer 1 of a four-layer intelligence model:

```
LAYER 4: Interaction Alpha ──── What the musician NEEDS
    │  (learned from human-AI session data)
    │
LAYER 3: Structural Signals ─── Where the music is GOING
    │  (self-similarity, novelty detection, arc position)
    │
LAYER 2: Temporal Indicators ── What the audio is DOING
    │  (delta features, momentum, volatility, regime)
    │
LAYER 1: Instantaneous Features ── What the audio IS  ◄── v1 is here
    │  (chroma, BPM, key, energy, centroid, onset)
    │
RAW AUDIO
```

Each layer feeds the next. Each layer makes the AI generation smarter:

- **v1** (now): *"124 BPM, D minor, energetic"*
- **v2**: *"accelerating toward 130, energy building, locked in D minor"*
- **v3**: *"build phase, 4 measures from peak, tension rising"*
- **v4**: *[direct parameter conditioning — no natural language needed]*

The full framework is in [`specs/05-SONIC-ALPHA.md`](specs/05-SONIC-ALPHA.md).

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Audio analysis | librosa 0.10 | Industry standard MIR, CQT chroma, beat tracking |
| Key detection | Krumhansl-Schmuckler | Established musicology (1990), correlates chroma with key profiles |
| AI generation | MusicGen-Small (audiocraft) | 300M params, MIT license, text-conditioned, 10s clips |
| Server | FastAPI + uvicorn | Async WebSocket support, automatic OpenAPI docs |
| Store | DictStore / Redis | Thread-safe in-memory default, Redis optional with pipeline writes |
| Frontend | Vanilla JS + Canvas 2D | No build step, no frameworks, <200 lines |
| Audio I/O | sounddevice | Cross-platform mic, callback-based, no PortAudio install on macOS |

**Device selection for MusicGen:**
- CUDA → FP16 (fastest — RTX 5090 target)
- MPS → FP32 (Apple Silicon, audiocraft MPS is unstable with FP16)
- CPU → FP32 (fallback, ~40s per clip)

---

## Tests

```bash
make test                                          # 65 non-integration tests
make redis-up && pytest tests/ -v                  # + 3 Redis integration tests
pytest tests/test_generation.py -v                 # Generation engine (mocked, no GPU)
python3 scripts/benchmark_generation.py            # Time MusicGen on your hardware
```

68 tests covering feature extraction, prompt building, store operations, API endpoints, WebSocket lifecycle, and generation engine (mocked).

---

## Project Structure

```
sonic-store/
├── src/                    # All Python source
│   ├── ingestion/          # Mic + file audio input
│   ├── features/           # MIR feature extraction
│   ├── store/              # Feature state persistence
│   ├── generation/         # MusicGen prompt + inference
│   └── api/                # FastAPI server
├── ui/                     # Browser dashboard (HTML/JS/CSS)
├── tests/                  # 68 pytest tests
├── scripts/                # Utilities (fixtures, benchmark, demo loader)
├── demo/                   # Drop WAV files here for demo mode
├── specs/                  # Architecture, roadmap, Sonic Alpha framework
├── research/               # 28 completed research documents
├── requirements.txt        # Production dependencies
├── Makefile                # install, run, test, redis-up
└── .env.example            # Configuration template
```

---

## License

MIT

---

*Built by Danny (Composer) and Quincy (Producer/Technical Director)*
*For the love of music and the machines that listen*
