# SonicStore — System Architecture
**Version:** 1.0  
**Date:** 2026-04-16  
**Status:** APPROVED FOR IMPLEMENTATION  
**Author:** Technical Director

---

## 0. Locked Decisions (Do Not Revisit)

| Decision | Value |
|---|---|
| Latency target | <2s feature loop; <8s total play-to-hear cycle |
| Product identity | Feature Store + Feedback Loop |
| License | MIT |
| Model stack | librosa, audiocraft (MusicGen-Small), sounddevice |
| Deployment | Local-only, single machine, no network dependencies |

---

## 1. System Overview

### 1.1 ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          SonicStore v1                              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐  │
│  │    AUDIO     │    │    FEATURE       │    │    HOT STORE      │  │
│  │  INGESTION   │───▶│    ENGINE        │───▶│    (Redis)        │  │
│  │              │    │                  │    │                   │  │
│  │ • Mic input  │    │ • chroma (12d)   │    │ features:latest   │  │
│  │ • File upload│    │ • BPM            │    │ features:history  │  │
│  │ • Chunking   │    │ • key            │    │                   │  │
│  └──────────────┘    │ • RMS energy     │    └────────┬──────────┘  │
│                      │ • spectral cent. │             │             │
│                      │ • onset strength │    ┌────────▼──────────┐  │
│                      │ • mel spectrogram│    │    FEATURE API    │  │
│                      └──────────────────┘    │    (FastAPI)      │  │
│                                              │                   │  │
│  ┌──────────────────────────────────────┐    │ POST /analyze     │  │
│  │         GENERATION ENGINE           │    │ GET  /features/*  │  │
│  │                                     │◀───│ WS   /ws/features │  │
│  │ • Feature-to-prompt translation     │    └────────┬──────────┘  │
│  │ • MusicGen-Small (300M, FP16)        │             │             │
│  │ • Background thread (non-blocking)  │    ┌────────▼──────────┐  │
│  │ • 10-second audio clips             │    │      WEB UI       │  │
│  └──────────────────────────────────────┘    │  (Vanilla JS)     │  │
│                      │                      │                   │  │
│                      │ generated audio      │ • Live waveform   │  │
│                      └─────────────────────▶│ • Chroma heatmap  │  │
│                                             │ • Feature gauges  │  │
│                                             │ • Audio playback  │  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow (End-to-End)

```
1. CAPTURE
   Mic → sounddevice callback → numpy float32 array (sr=22050, chunk=2s)

2. FEATURE EXTRACTION
   numpy array → librosa → FeatureVector dict → JSON serialization

3. STORE
   JSON → Redis SETEX features:latest (TTL=60s)
   JSON → Redis LPUSH features:history → LTRIM to last 30 entries

4. STREAM TO UI
   Redis GET → FastAPI WebSocket → browser → Canvas/Chart.js render

5. GENERATION TRIGGER
   features:latest read by GenerationEngine (polling, 3s interval)
   FeatureVector → prompt_builder() → text string
   text string → MusicGen-Small.generate() → torch.Tensor
   Tensor → WAV bytes → base64 encode → WebSocket → browser AudioContext

6. CYCLE REPEAT
   Browser plays audio → musician responds → mic captures → step 1
```

### 1.3 Component Inventory

| Component | File | Responsibility |
|---|---|---|
| AudioIngestion | `src/ingestion/mic.py` | Capture mic chunks via sounddevice; normalize to float32 |
| FileIngestion | `src/ingestion/file.py` | Load audio files via librosa; chunk into windows |
| FeatureEngine | `src/features/engine.py` | Extract all 7 feature types from audio chunks |
| HotStore | `src/store/redis_store.py` | Read/write feature state in Redis; Python dict fallback |
| FeatureAPI | `src/api/app.py` | FastAPI app: REST endpoints + WebSocket server |
| GenerationEngine | `src/generation/engine.py` | Feature-to-prompt + MusicGen inference in background thread |
| PromptBuilder | `src/generation/prompt.py` | Convert FeatureVector to MusicGen text prompt |
| WebUI | `ui/index.html` + `ui/app.js` | Single-page app; WebSocket client; Canvas rendering |

---

## 2. Component Design

### 2.1 Audio Ingestion

**Responsibilities:** Accept audio from mic or file; emit fixed-size overlapping chunks.

**Mic Input (`src/ingestion/mic.py`)**

```python
SAMPLE_RATE = 22050       # Hz — librosa native rate
CHUNK_SECONDS = 2.0       # seconds per analysis window
HOP_SECONDS = 1.0         # advance between windows (50% overlap)
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)  # 44100 samples
CHANNELS = 1              # mono
DTYPE = "float32"
```

sounddevice `InputStream` callback accumulates samples into a ring buffer. When the buffer holds `CHUNK_SAMPLES` new samples beyond the last hop, a `numpy.ndarray` of shape `(44100,)` is pushed to a `queue.Queue[np.ndarray]`.

The ring buffer keeps the last `CHUNK_SAMPLES` at all times so each window includes the trailing `HOP_SECONDS` of the previous window. This ensures transients that straddle a boundary are captured in at least one window.

**File Input (`src/ingestion/file.py`)**

`librosa.load(path, sr=22050, mono=True)` returns the full waveform. A generator function yields chunks of `CHUNK_SAMPLES` with `HOP_SAMPLES` advance, emitting the same `numpy.ndarray` shape as the mic path. The `POST /analyze` endpoint calls this generator and drives the feature engine synchronously.

**Output contract:** `np.ndarray` of dtype `float32`, shape `(44100,)`, values in `[-1.0, 1.0]`.

---

### 2.2 Feature Engine

**Responsibilities:** Accept one audio chunk; return one FeatureVector.

**File:** `src/features/engine.py`

All extraction uses librosa 0.10.x. The function is pure and synchronous — no I/O, no side effects.

```python
def extract_features(
    audio: np.ndarray,           # float32, shape (44100,)
    sr: int = 22050,
) -> FeatureVector:
    ...
```

**Feature extraction details:**

| Feature | librosa call | Output shape | Notes |
|---|---|---|---|
| chroma | `librosa.feature.chroma_cqt(y, sr)` | `(12,)` mean over time frames | CQT-based, more robust than STFT chroma |
| bpm | `librosa.beat.beat_track(y, sr)` | scalar float | returns `(tempo, beat_frames)`, use tempo |
| key | custom from chroma | scalar int 0-11 + mode | argmax of chroma gives pitch class; mode from chroma profile correlation |
| rms_energy | `librosa.feature.rms(y)` | scalar float | mean over frames, then linearized to 0-1 |
| spectral_centroid | `librosa.feature.spectral_centroid(y, sr)` | scalar float (Hz) | mean over frames |
| onset_strength | `librosa.onset.onset_strength(y, sr)` | scalar float | mean over frames |
| mel_spectrogram | `librosa.feature.melspectrogram(y, sr, n_mels=128)` | `(128, T)` float32 | used for heatmap display only; not sent to prompt |

**Key detection** uses Krumhansl-Schmuckler key profiles correlated against the mean chroma vector. Returns `(pitch_class: int, mode: str)` where mode is `"major"` or `"minor"`.

**Target latency:** <500ms for a 2-second chunk on both M3 Max and RTX 4080 host CPU. librosa operations on a 44100-sample float32 array typically run in 50-150ms on modern CPUs. The 500ms budget is a 3-4x safety margin.

---

### 2.3 Hot Store

**Responsibilities:** Persist latest features for API reads; maintain history ring for timeline display.

**File:** `src/store/redis_store.py`

**Redis schema:**

```
features:latest   STRING   JSON-encoded FeatureVector   TTL=60s
features:history  LIST     JSON-encoded FeatureVector   capped at 30 entries
```

Write pattern:
```python
pipe = redis.pipeline()
pipe.setex("features:latest", 60, json.dumps(feature_vector))
pipe.lpush("features:history", json.dumps(feature_vector))
pipe.ltrim("features:history", 0, 29)
pipe.execute()
```

**Fallback (no Redis installed):** `src/store/dict_store.py` implements the same interface using a Python dict and `collections.deque(maxlen=30)`. The API layer selects the backend at startup:

```python
try:
    import redis
    store = RedisStore(host="localhost", port=6379)
    store.ping()
except Exception:
    store = DictStore()
    print("Redis unavailable — using in-memory store")
```

This means Redis is optional. The demo works without it.

---

### 2.4 Feature API

**Responsibilities:** Expose features over HTTP and WebSocket; bridge mic ingestion to UI.

**File:** `src/api/app.py`

FastAPI application. Runs on `localhost:8000`.

**Endpoints:**

```
POST /analyze
  Request:  multipart/form-data  { file: audio_file }
  Response: FeatureVector (JSON)
  Behavior: Loads file, extracts features from first 2s chunk, stores to hot store, returns

GET /features/latest
  Response: FeatureVector (JSON) | 404 if no data yet

GET /features/history
  Query params: limit=int (default 30, max 30)
  Response: FeatureVector[] (JSON array, newest first)

GET /features/stream-trigger
  Query params: interval=float (default 1.0, how often to trigger generation)
  Response: 200 OK
  Behavior: Sets the generation trigger interval in the GenerationEngine

WebSocket /ws/features
  Server pushes: FeatureMessage (JSON) on each new feature extraction
  Server pushes: GenerationMessage (JSON) when audio clip is ready
  Client sends:  ControlMessage (JSON) for start/stop
```

**WebSocket lifecycle:**

1. Client connects to `/ws/features`
2. Server registers client in `ConnectionManager`
3. On each new feature extraction, `ConnectionManager.broadcast(FeatureMessage)` is called
4. On new generated audio, `ConnectionManager.broadcast(GenerationMessage)` is called
5. Client disconnect removes from registry

**Background mic loop** is started as a FastAPI lifespan task (`asyncio.create_task`). It reads from the ingestion queue and drives the feature engine + store + broadcast on each chunk.

---

### 2.5 Generation Engine

**Responsibilities:** Observe feature state; build prompt; call MusicGen; emit audio to UI.

**File:** `src/generation/engine.py`

Runs in a `threading.Thread` (not asyncio — PyTorch is not async-safe). Communicates with the FastAPI process via a thread-safe `queue.Queue[GeneratedClip]`.

**Generation loop:**

```python
while running:
    time.sleep(GENERATION_INTERVAL)   # default 3.0 seconds
    features = store.get_latest()
    if features is None:
        continue
    if features.timestamp == last_generated_timestamp:
        continue                        # no new audio, skip
    prompt = build_prompt(features)
    clip = generate_clip(prompt)        # blocking, ~2-6s
    output_queue.put(GeneratedClip(audio_b64=..., prompt=prompt, duration=10.0))
    last_generated_timestamp = features.timestamp
```

**MusicGen configuration:**

```python
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained("facebook/musicgen-small")
model.set_generation_params(
    duration=10,          # seconds
    use_sampling=True,
    top_k=250,
    temperature=1.0,
)
```

Model is loaded once at startup (`src/generation/engine.py` module-level). First load downloads ~600MB to `~/.cache/huggingface/hub/`. Subsequent starts load from cache in ~3-5s.

**FP16 on CUDA:** If `torch.cuda.is_available()`, the model is cast to `float16` after loading. On M3 Max (MPS), keep `float32` — MPS FP16 support for audiocraft is inconsistent. Note: an MLX port of MusicGen exists (`mlx-examples/musicgen`) which may perform better on Apple Silicon, but for hackathon simplicity we use standard audiocraft with MPS/CPU fallback.

```python
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
if device == "cuda":
    model = model.half()
model = model.to(device)
```

**Output:** `torch.Tensor` of shape `(1, 1, samples)` → squeeze → numpy → `scipy.io.wavfile` bytes → base64 encode → JSON string.

---

### 2.6 Prompt Builder

**Responsibilities:** Translate a FeatureVector into a MusicGen text prompt.

**File:** `src/generation/prompt.py`

```python
def build_prompt(features: FeatureVector) -> str:
    ...
```

**Mapping table:**

| Feature | Range | Prompt fragment |
|---|---|---|
| bpm | <70 | "slow" |
| bpm | 70-100 | "moderate tempo" |
| bpm | 100-130 | "upbeat" |
| bpm | >130 | "fast" |
| key + mode | C major | "in C major" |
| key + mode | A minor | "in A minor" |
| ... | all 24 keys | `KEY_NAMES[pitch_class] + " " + mode` |
| rms_energy | <0.1 | "quiet, delicate" |
| rms_energy | 0.1-0.4 | "moderate energy" |
| rms_energy | >0.4 | "energetic, driving" |
| spectral_centroid | <1500 Hz | "warm, bass-heavy" |
| spectral_centroid | 1500-3500 Hz | "balanced" |
| spectral_centroid | >3500 Hz | "bright, airy" |

**Template:**

```python
f"{energy_descriptor} {timbre_descriptor} musical accompaniment, "
f"{tempo_descriptor}, {bpm:.0f} BPM, {key_name} {mode}, "
f"complementary to the input melody, instrumental"
```

**Example output:** `"upbeat balanced musical accompaniment, 124 BPM, D major, complementary to the input melody, instrumental"`

The prompt is logged to stdout so the musician can see what the model received.

---

### 2.7 Web UI

**Responsibilities:** Display features in real-time; play generated audio; provide start/stop controls.

**Files:** `ui/index.html`, `ui/app.js`, `ui/style.css`

**Served by FastAPI** via `StaticFiles` mount at `/ui`. Browser opens `http://localhost:8000/ui`.

**Layout (no framework, Canvas + vanilla JS):**

```
┌─────────────────────────────────────────────────────┐
│  SonicStore                          [Start] [Stop]  │
├─────────────────┬───────────────────────────────────┤
│  WAVEFORM       │  FEATURE DASHBOARD                 │
│  (Canvas)       │  BPM: 124  KEY: D major            │
│                 │  Energy: ████░░  0.42               │
│                 │  Spectral: 2300 Hz                 │
├─────────────────┴───────────────────────────────────┤
│  CHROMA HEATMAP (Canvas, 12 rows × 30 time columns)  │
├─────────────────────────────────────────────────────┤
│  AI RESPONSE                                         │
│  Prompt: "upbeat balanced accompaniment, 124 BPM..."  │
│  [▶ Play generated clip]          Generated: 3.2s ago│
└─────────────────────────────────────────────────────┘
```

**Waveform canvas:** Draws last 2 seconds of incoming audio samples. Updated at ~10fps from the FeatureMessage (which includes the raw waveform array trimmed to 2048 points for display).

**Chroma heatmap canvas:** 12 rows (pitch classes C through B) × 30 columns (time). Color mapped HSL: value 0 = dark blue, value 1 = bright yellow. Columns shift left on each new feature message; newest column appended on right.

**Feature dashboard:** DOM text updates. No Canvas needed. BPM rounded to integer. Energy mapped to a CSS width bar (0-100%). Key displayed as string.

**Audio playback:** `GenerationMessage.audio_b64` is decoded to `ArrayBuffer`, decoded by `AudioContext.decodeAudioData()`, played via `AudioBufferSourceNode`. No file I/O. The previous clip is stopped before the new one plays.

**WebSocket reconnect:** On close event, retry after 2s with exponential backoff (max 30s).

---

## 3. Interface Contracts

### 3.1 FeatureVector JSON Schema

```typescript
interface FeatureVector {
  // Metadata
  timestamp: number;            // Unix ms (Date.now())
  chunk_index: number;          // incrementing counter
  source: "mic" | "file";
  duration_seconds: number;     // always 2.0 for mic; may vary for file

  // Tonal
  chroma: number[];             // length 12, values 0.0–1.0, index 0 = C
  bpm: number;                  // float, e.g. 124.3
  key_pitch_class: number;      // int 0–11, 0=C, 1=C#, ..., 11=B
  key_mode: "major" | "minor";

  // Energy / Dynamics
  rms_energy: number;           // float 0.0–1.0 (normalized)
  spectral_centroid_hz: number; // float, e.g. 2300.5

  // Rhythm
  onset_strength: number;       // float 0.0–1.0 (normalized mean)

  // Spectrogram (display only, not sent to prompt)
  mel_spectrogram: number[][];  // shape [128][T], float32, power in dB
                                // T = ~87 frames for 2s at sr=22050, hop=512

  // Display waveform (downsampled)
  waveform_display: number[];   // length 2048, float32, values -1.0 to 1.0
}
```

**Normalization conventions:**
- `rms_energy`: `min-max` normalized against a rolling 60-second window. Raw value is in range 0–0.3 typically; displayed as 0–1.
- `onset_strength`: same rolling normalization.
- `chroma`: librosa outputs 0–1 already; no normalization needed.
- `mel_spectrogram`: power-to-dB (`librosa.power_to_db`) then normalized to 0–1 per frame for display.

---

### 3.2 WebSocket Message Format

All messages are JSON. The `type` field discriminates.

**FeatureMessage (server → client)**

```typescript
interface FeatureMessage {
  type: "features";
  data: FeatureVector;
}
```

**GenerationMessage (server → client)**

```typescript
interface GenerationMessage {
  type: "generation";
  data: {
    audio_b64: string;          // base64-encoded WAV (mono, 32kHz, ~10s)
    prompt: string;             // the text prompt that was used
    duration_seconds: number;   // actual generated length (always ~10.0)
    generation_time_ms: number; // wall-clock ms from prompt to audio ready
    features_snapshot: FeatureVector; // the features that triggered generation
  };
}
```

**ControlMessage (client → server)**

```typescript
interface ControlMessage {
  type: "control";
  action: "start_mic" | "stop_mic" | "trigger_generation";
}
```

**ErrorMessage (server → client)**

```typescript
interface ErrorMessage {
  type: "error";
  code: "mic_unavailable" | "extraction_failed" | "generation_failed";
  message: string;
}
```

---

### 3.3 REST API Shapes

**POST /analyze**

```
Request:  multipart/form-data
  file: binary audio (wav, mp3, flac, ogg — anything librosa supports)

Response 200:
  Content-Type: application/json
  Body: FeatureVector

Response 422:
  Body: { "detail": "unsupported file format" | "file too short (<0.5s)" }
```

**GET /features/latest**

```
Response 200:
  Content-Type: application/json
  Body: FeatureVector

Response 404:
  Body: { "detail": "no features extracted yet" }
```

**GET /features/history**

```
Query params:
  limit: int, optional, default=30, max=30

Response 200:
  Content-Type: application/json
  Body: FeatureVector[]   (array, newest first)
  (empty array if no history)
```

---

## 4. Technology Stack

| Library | Version | Justification |
|---|---|---|
| Python | 3.11 | Required by audiocraft; 3.12 has audiocraft compatibility issues |
| FastAPI | 0.111.x | Async WebSocket support; automatic OpenAPI docs; fastest Python ASGI |
| uvicorn | 0.29.x | ASGI server; `--reload` dev mode |
| Redis | 5.x (server) | Feature state; LPUSH/LTRIM for history ring; optional (dict fallback) |
| redis-py | 5.0.x | Python client; pipeline support for atomic writes |
| librosa | 0.10.x | Industry standard MIR; CQT chroma, beat tracking, mel spectrogram |
| numpy | 1.26.x | Constrained by audiocraft/librosa compatibility |
| sounddevice | 0.4.x | Cross-platform mic access; callback-based; no portaudio install on macOS |
| audiocraft | 1.3.x | MusicGen-Small; MIT/CC-BY; audiocraft = Facebook's official package |
| torch | 2.2.x | Required by audiocraft; 2.2 has stable MPS support for M-series |
| torchaudio | 2.2.x | Audio I/O for saving generated clips |
| scipy | 1.12.x | WAV encoding for generated clips |
| python-multipart | 0.0.9 | FastAPI file upload support |

**Frontend (no build step):**

All rendering uses Canvas 2D API directly. No charting libraries — Chart.js re-renders entire charts on update and lags at 50Hz. Canvas `fillRect` for chroma heatmap and `lineTo` for waveform are ~20 lines each and update in `requestAnimationFrame` without frame drops.

---

## 5. Performance Budgets

| Stage | Budget | Measurement point | Hardware assumption |
|---|---|---|---|
| Mic capture latency | <50ms | sounddevice callback → queue | All hardware |
| Feature extraction | <500ms | `extract_features()` wall time | M3 Max CPU / i9 CPU |
| Redis write | <5ms | `store.write()` wall time | localhost |
| WebSocket broadcast | <20ms | server `send_json()` → client `onmessage` | localhost |
| Feature-to-UI total | <100ms | mic chunk complete → DOM updated | localhost |
| Generation (M3 Max) | <6s | `model.generate()` wall time | MPS, FP32 |
| Generation (RTX 4080) | <4s | `model.generate()` wall time | CUDA, FP16 |
| Total loop (play → hear AI) | <8s | mic capture start → browser AudioContext.play() | Either hardware |

**Budget breakdown for total loop:**

```
Mic capture (1s chunk advance)         ~1000ms
Feature extraction                      ~200ms
Redis write + WebSocket push             ~25ms
Generation trigger check (3s interval)  ~3000ms  (worst case: missed this cycle)
MusicGen generation                     ~5000ms  (M3 Max worst case)
WebSocket push + audio decode            ~100ms
                                        -------
Total worst case                        ~9325ms
Total typical case                      ~6500ms (gen not at worst case)
```

Note: The 3-second polling interval means generation is triggered within 3s of new features arriving, not immediately. Reducing `GENERATION_INTERVAL` to 1.5s brings worst-case total loop to ~7s on M3 Max.

---

## 6. Directory Structure

```
sonic-store/
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── mic.py              # sounddevice mic → queue
│   │   └── file.py             # librosa file → chunk generator
│   ├── features/
│   │   ├── __init__.py
│   │   ├── engine.py           # extract_features(audio) → FeatureVector
│   │   ├── key_detection.py    # Krumhansl-Schmuckler key profiles
│   │   └── normalization.py    # Rolling min-max normalizer
│   ├── store/
│   │   ├── __init__.py
│   │   ├── base.py             # AbstractStore protocol
│   │   ├── redis_store.py      # Redis implementation
│   │   └── dict_store.py       # In-memory fallback
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── engine.py           # Background thread; MusicGen inference loop
│   │   └── prompt.py           # build_prompt(FeatureVector) → str
│   └── api/
│       ├── __init__.py
│       ├── app.py              # FastAPI app; mounts /ui; registers lifespan tasks
│       ├── websocket.py        # ConnectionManager; broadcast helpers
│       ├── routes_analyze.py   # POST /analyze
│       └── routes_features.py  # GET /features/*
├── ui/
│   ├── index.html              # Single page; loads app.js; no build step
│   ├── app.js                  # WebSocket client; Canvas rendering; AudioContext
│   └── style.css               # Minimal styling; dark theme for demo
├── tests/
│   ├── test_features.py        # Unit tests for extract_features (offline audio)
│   ├── test_prompt.py          # Unit tests for build_prompt
│   ├── test_store.py           # Unit tests for DictStore; Redis integration test
│   └── test_api.py             # FastAPI TestClient tests
├── scripts/
│   ├── generate_test_audio.py  # Create WAV files for testing without a mic
│   └── benchmark_generation.py # Measure MusicGen latency on current hardware
├── requirements.txt            # Pinned production deps
├── requirements-dev.txt        # pytest, httpx (for TestClient)
├── .env.example                # REDIS_URL, GENERATION_INTERVAL, etc.
├── Makefile                    # make run, make test, make install
└── README.md                   # Setup and demo instructions
```

**Makefile targets:**

```makefile
install:    pip install -r requirements.txt
run:        uvicorn src.api.app:app --reload --port 8000
test:       pytest tests/ -v
redis-up:   redis-server --daemonize yes
```

---

## 7. Startup Sequence

When `uvicorn src.api.app:app` starts:

1. FastAPI lifespan `startup` event fires
2. Store backend is selected (Redis or dict fallback) and tested
3. `GenerationEngine.__init__()` is called — this triggers `MusicGen.get_pretrained()` download/load. First run: ~30-60s. Cached run: ~5-10s. Progress is logged to stdout.
4. `GenerationEngine.start()` launches the background thread
5. `MicIngestion.start()` launches the sounddevice input stream (or waits for `start_mic` WebSocket control message — configurable)
6. Server is ready; logs `Uvicorn running on http://127.0.0.1:8000`

**Mic start behavior:** By default, mic is not auto-started on server launch. The UI sends `{"type":"control","action":"start_mic"}` when the user clicks Start. This avoids permission dialogs before the user is ready.

---

## 8. Configuration

All config via environment variables (`.env` file loaded by `python-dotenv`):

```bash
REDIS_URL=redis://localhost:6379/0    # optional; falls back to dict store
GENERATION_INTERVAL=3.0               # seconds between generation checks
MUSICGEN_MODEL=facebook/musicgen-small
MUSICGEN_DURATION=10                  # seconds of generated audio
AUDIO_SAMPLE_RATE=22050
AUDIO_CHUNK_SECONDS=2.0
AUDIO_HOP_SECONDS=1.0
HISTORY_MAX_ENTRIES=30
PORT=8000
```

---

## 9. Testability

Each component is independently testable:

| Component | Test approach | Test fixture |
|---|---|---|
| FeatureEngine | Pass pre-recorded WAV as numpy array | `tests/fixtures/440hz_sine_2s.wav` |
| PromptBuilder | Assert string contains expected fragments for known inputs | Hardcoded FeatureVector dict |
| DictStore | Instantiate directly; call read/write; assert state | No external deps |
| RedisStore | Requires running Redis; mark as `@pytest.mark.integration` | Local Redis |
| FastAPI routes | `httpx.AsyncClient(app=app)` for REST; `TestClient` for sync | DictStore injected |
| GenerationEngine | Mock `MusicGen.generate()` to return silence tensor; assert output queue populated | monkeypatch |

---

## 10. Explicitly Out of Scope for v1

The following are non-goals. Do not design, implement, or stub them.

| Feature | Why deferred |
|---|---|
| RAVE real-time tier (<50ms) | Requires C++/Rust FFI; out of scope per Decision 1 |
| Multi-user support | Single machine, single user |
| Cloud deployment | Local-only per hardware targets |
| DAW plugin (VST/AU) | Separate product; different tech stack |
| Mobile app | No network dependencies means no mobile |
| Authentication / auth | Single user, local machine |
| Persistent storage beyond Redis | No DuckDB, no SQLite, no S3 |
| Multiple concurrent models | One MusicGen-Small instance only |
| Fine-tuning / training | Inference only |
| MIDI output | Audio output only |
| Streaming generation | Generate-then-play only; full 10s clip before playback |
| Essentia integration | librosa covers all required features for v1 |
| Docker / containerization | Local install via pip; container adds complexity without benefit for demo |

---

## 11. Integration Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| audiocraft install fails (torch version conflict) | Medium | Pin exact versions in requirements.txt; test on clean venv |
| MPS support unstable for audiocraft on M3 | Medium | Fallback to CPU if MPS raises; CPU generates 10s clip in ~40s (acceptable with warning) |
| sounddevice mic permissions on macOS | Low | Document in README; UI shows clear "Grant microphone access" instruction |
| Redis not installed | Medium | DictStore fallback is seamless; log warning only |
| MusicGen cold load blocks server startup | Low | Load in background thread; server starts immediately; UI shows "Model loading..." state |
| WebSocket disconnects lose audio | Low | GenerationMessage includes full audio_b64; no streaming chunks to lose |
| Chroma heatmap lag on slow machines | Low | Downsample to 2048 waveform points; cap Canvas at 30fps |

---

*Architecture document by: Technical Director*  
*For: Implementation agents and Danny (Composer)*  
*Next: specs/03-ROADMAP.md — implementation sequence and 48-hour task breakdown*
