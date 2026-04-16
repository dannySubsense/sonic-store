# SonicStore — Implementation Roadmap
**Version:** 1.0
**Date:** 2026-04-16
**Status:** READY FOR IMPLEMENTATION
**Author:** Technical Director

---

## 0. How to Read This Document

Slices are numbered and ordered by dependency. Each slice must be fully complete — all tests passing — before the next slice begins. No partial work. No skipping ahead.

**Total pre-hackathon slices:** 11
**Total estimated build time:** 42-55 hours of focused work
**Available window:** April 16 – June 5 (7 weeks, ~7 hours/week)

---

## 1. Dependency Map

| Unit | Depends On |
|------|-----------|
| `src/features/engine.py` | numpy, librosa (installed) |
| `src/features/key_detection.py` | `src/features/engine.py` |
| `src/features/normalization.py` | numpy only |
| `src/generation/prompt.py` | FeatureVector schema (from engine.py) |
| `src/store/base.py` | nothing |
| `src/store/dict_store.py` | `src/store/base.py` |
| `src/store/redis_store.py` | `src/store/base.py`, redis-py |
| `src/api/app.py` | store, features engine, ingestion |
| `src/api/websocket.py` | `src/api/app.py` |
| `src/api/routes_analyze.py` | feature engine, store, file ingestion |
| `src/api/routes_features.py` | store |
| `src/ingestion/file.py` | librosa, numpy |
| `src/ingestion/mic.py` | sounddevice, numpy |
| `src/generation/engine.py` | prompt builder, store, audiocraft |
| `ui/index.html` | FastAPI static serving |
| `ui/app.js` | WebSocket endpoint live |
| Full loop | all of the above |

---

## 2. Slice Overview

| Slice | Name | Depends On | Est. Hours |
|-------|------|------------|------------|
| S01 | Project Scaffolding | — | 1–2h |
| S02 | Feature Engine (offline) | S01 | 3–4h |
| S03 | Prompt Builder | S02 | 2–3h |
| S04 | Store Layer | S01 | 2–3h |
| S05 | REST API (file upload + GET) | S02, S03, S04 | 3–4h |
| S06 | WebSocket Server | S05 | 2–3h |
| S07 | Web UI (static dashboard) | S06 | 4–5h |
| S08 | Mic Ingestion | S01 | 2–3h |
| S09 | Mic Loop (live feature pipeline) | S06, S08 | 2–3h |
| S10 | Generation Engine (MusicGen) | S05, S06 | 4–6h |
| S11 | Polish + Demo Mode | S09, S10 | 3–4h |

---

## 3. Slice Detail

---

### S01: Project Scaffolding

**Goal:** A clean, runnable project skeleton with all dependencies installable and a passing smoke test.

**Depends On:** —

**Estimated Time:** 1–2 hours

**Files to Create:**

- `requirements.txt` — create
- `requirements-dev.txt` — create
- `.env.example` — create
- `Makefile` — create
- `src/__init__.py` — create (empty)
- `src/ingestion/__init__.py` — create (empty)
- `src/features/__init__.py` — create (empty)
- `src/store/__init__.py` — create (empty)
- `src/generation/__init__.py` — create (empty)
- `src/api/__init__.py` — create (empty)
- `tests/__init__.py` — create (empty)
- `tests/fixtures/.gitkeep` — create (placeholder)
- `scripts/.gitkeep` — create (placeholder)
- `ui/.gitkeep` — create (placeholder)
- `scripts/generate_test_audio.py` — create (generates test WAV fixtures)

**requirements.txt pin list:**

```
fastapi==0.111.1
uvicorn==0.29.0
python-multipart==0.0.9
redis==5.0.4
librosa==0.10.2
numpy==1.26.4
sounddevice==0.4.7
audiocraft==1.3.0
torch==2.2.2
torchaudio==2.2.2
scipy==1.12.0
python-dotenv==1.0.1
```

**requirements-dev.txt:**

```
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

**Makefile targets:**

```makefile
install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn src.api.app:app --reload --port 8000

test:
	pytest tests/ -v

redis-up:
	redis-server --daemonize yes
```

**.env.example:**

```bash
REDIS_URL=redis://localhost:6379/0
GENERATION_INTERVAL=3.0
MUSICGEN_MODEL=facebook/musicgen-small
MUSICGEN_DURATION=10
AUDIO_SAMPLE_RATE=22050
AUDIO_CHUNK_SECONDS=2.0
AUDIO_HOP_SECONDS=1.0
HISTORY_MAX_ENTRIES=30
PORT=8000
```

**scripts/generate_test_audio.py** must produce:
- `tests/fixtures/440hz_sine_2s.wav` — 440Hz sine, 2 seconds, mono, 22050Hz
- `tests/fixtures/silence_2s.wav` — silence, 2 seconds, mono, 22050Hz
- `tests/fixtures/chirp_2s.wav` — linear frequency sweep 200Hz–2000Hz, 2 seconds, mono, 22050Hz

**Testing Strategy:**

- Manual: `pip install -r requirements.txt` completes without error
- Manual: `python scripts/generate_test_audio.py` produces the three WAV files
- Manual: `python -c "import librosa, numpy, fastapi, sounddevice"` runs without ImportError

**Done When:**

- [ ] `pip install -r requirements.txt` completes on a clean Python 3.11 venv
- [ ] `pip install -r requirements-dev.txt` completes
- [ ] `python scripts/generate_test_audio.py` creates all three fixture WAV files
- [ ] All `__init__.py` files exist; directory tree matches architecture spec section 6
- [ ] `make test` runs (no tests yet, zero failures)

---

### S02: Feature Engine (Offline)

**Goal:** `extract_features()` accepts a numpy array and returns a validated FeatureVector dict, tested against known audio fixtures with no mic or network required.

**Depends On:** S01

**Estimated Time:** 3–4 hours

**Files to Create:**

- `src/features/key_detection.py` — create (Krumhansl-Schmuckler profiles)
- `src/features/normalization.py` — create (rolling min-max normalizer)
- `src/features/engine.py` — create (extract_features function)
- `tests/test_features.py` — create

**Key implementation notes:**

`key_detection.py` must define `KRUMHANSL_MAJOR` and `KRUMHANSL_MINOR` numpy arrays (24 values each, the standard KS profiles) and a function `detect_key(chroma_mean: np.ndarray) -> tuple[int, str]` that correlates the 12-element chroma vector against all 24 rotations of both profiles and returns `(pitch_class, mode)`.

`normalization.py` must define `RollingNormalizer` with a `update(value: float) -> float` method that maintains a rolling window (default 60 entries) and returns the min-max normalized value. Initialize min=0, max=1 to avoid division by zero on first call.

`engine.py` must define:

```python
def extract_features(
    audio: np.ndarray,   # float32, shape (44100,), values in [-1.0, 1.0]
    sr: int = 22050,
    chunk_index: int = 0,
    source: str = "file",
) -> dict:
    ...
```

Return dict must exactly match the FeatureVector schema from architecture section 3.1. `waveform_display` is the audio downsampled to 2048 points (use `np.interp` with evenly spaced indices). `mel_spectrogram` is converted to dB then normalized 0–1 per the architecture spec.

**Test cases in tests/test_features.py:**

The sine wave at 440Hz is close to A4 — test that `key_pitch_class` comes back as 9 (A) with reasonable tolerance (could be 8 or 10 due to 2-second window, accept ±1). BPM on a pure sine with no rhythm returns an arbitrary value — do not assert on BPM for the sine fixture. Assert type and shape only.

For the chirp fixture: assert `spectral_centroid_hz` is greater than 800Hz (broad-spectrum signal).

For silence: assert `rms_energy` is less than 0.05. Assert `waveform_display` has length 2048.

All tests use `librosa.load("tests/fixtures/440hz_sine_2s.wav", sr=22050, mono=True)[0]` to load the numpy array — no mic, no network.

**Testing Strategy:**

- `pytest tests/test_features.py -v` — all unit tests pass
- Manual: inspect printed output of `extract_features` on each fixture to verify no NaN values

**Done When:**

- [ ] `extract_features()` returns a dict with all keys from FeatureVector schema
- [ ] No NaN or inf values in any returned field for any of the three fixtures
- [ ] `chroma` is length 12, values in [0.0, 1.0]
- [ ] `waveform_display` is length 2048
- [ ] `mel_spectrogram` is a list of lists, shape approximately [128][T]
- [ ] `pytest tests/test_features.py` passes (all assertions)
- [ ] Feature extraction wall time on the sine fixture is under 2 seconds (print timing in tests)

---

### S03: Prompt Builder

**Goal:** `build_prompt()` converts any valid FeatureVector dict into a non-empty text string with expected fragments, with full coverage tests.

**Depends On:** S02

**Estimated Time:** 2–3 hours

**Files to Create:**

- `src/generation/prompt.py` — create
- `tests/test_prompt.py` — create

**prompt.py must define:**

```python
KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def build_prompt(features: dict) -> str:
    ...
```

The mapping table from architecture section 2.6 must be implemented exactly. Test against boundary conditions (BPM exactly 70, exactly 100, exactly 130 — pick one side or the other and document which).

**Test cases in tests/test_prompt.py:**

Define at least 6 hardcoded FeatureVector dicts covering:

1. Slow + quiet + bass-heavy (bpm=60, rms_energy=0.05, spectral_centroid_hz=1000, key_pitch_class=0, key_mode="major")
2. Upbeat + energetic + bright (bpm=120, rms_energy=0.5, spectral_centroid_hz=4000, key_pitch_class=9, key_mode="minor")
3. Moderate everything (bpm=85, rms_energy=0.25, spectral_centroid_hz=2500, key_pitch_class=5, key_mode="major")
4. Fast + energetic (bpm=145, rms_energy=0.6, spectral_centroid_hz=3000, key_pitch_class=2, key_mode="minor")
5. BPM boundary at 100 (whichever side you pick, document it)
6. BPM boundary at 130

For each test: assert the prompt string contains the expected tempo descriptor, expected key string, and expected energy/timbre descriptor. Assert the prompt ends with "instrumental". Assert the prompt includes the BPM value as an integer.

**Testing Strategy:**

- `pytest tests/test_prompt.py -v` — all 6+ tests pass
- Manual: print prompts for all test cases and review for human-readable quality

**Done When:**

- [ ] `build_prompt()` returns a non-empty string for all 6 test FeatureVectors
- [ ] All BPM boundary conditions are tested and documented in comments
- [ ] Prompt always contains "instrumental" at the end
- [ ] Prompt always contains the key name (e.g., "D major" or "A minor")
- [ ] `pytest tests/test_prompt.py` passes

---

### S04: Store Layer

**Goal:** Both `DictStore` and `RedisStore` implement the `AbstractStore` protocol; `DictStore` tests pass without Redis; `RedisStore` integration test passes with Redis running.

**Depends On:** S01

**Estimated Time:** 2–3 hours

**Files to Create:**

- `src/store/base.py` — create
- `src/store/dict_store.py` — create
- `src/store/redis_store.py` — create
- `tests/test_store.py` — create

**base.py must define an `AbstractStore` protocol (use `typing.Protocol`):**

```python
class AbstractStore(Protocol):
    def write_latest(self, features: dict) -> None: ...
    def read_latest(self) -> dict | None: ...
    def read_history(self, limit: int = 30) -> list[dict]: ...
    def ping(self) -> bool: ...
```

**DictStore** uses `threading.Lock` for thread safety. History is `collections.deque(maxlen=30)`. `write_latest` also appends to history. `read_history(limit)` returns newest-first (reverse insertion order).

**RedisStore** uses the pipeline write pattern from architecture section 2.3 exactly. `ping()` calls `redis.ping()` and returns True/False. Wrap the constructor to accept `url: str` and use `redis.from_url(url)`.

**Store selection helper** in `src/store/__init__.py`:

```python
def get_store() -> AbstractStore:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        store = RedisStore(url)
        if store.ping():
            print(f"[store] Using Redis at {url}")
            return store
    except Exception as e:
        print(f"[store] Redis unavailable ({e}) — using in-memory store")
    return DictStore()
```

**Test cases in tests/test_store.py:**

Unit tests (no Redis required):
1. `DictStore().read_latest()` returns None on fresh instance
2. Write a FeatureVector dict, read_latest returns it
3. Write 35 entries, `read_history()` returns at most 30 (deque maxlen)
4. `read_history(limit=5)` returns at most 5 entries
5. `read_history()` returns newest-first (last written is index 0)
6. Concurrent writes from 2 threads complete without race condition (use threading.Barrier)

Integration tests (mark with `@pytest.mark.integration`):
7. `RedisStore` ping returns True with local Redis
8. Write + read_latest round-trip via Redis
9. History ring cap at 30 entries via Redis

**Testing Strategy:**

- `pytest tests/test_store.py -v -m "not integration"` — unit tests pass without Redis
- `make redis-up && pytest tests/test_store.py -v` — all tests including integration pass

**Done When:**

- [ ] `DictStore` passes all 6 unit tests
- [ ] `DictStore` and `RedisStore` are both assignable to `AbstractStore` protocol (mypy or duck typing)
- [ ] `get_store()` in `src/store/__init__.py` returns DictStore when Redis is unavailable
- [ ] Thread safety test passes (no assertion errors under concurrent access)
- [ ] `pytest tests/test_store.py -m "not integration"` exits 0

---

### S05: REST API (File Upload + GET Endpoints)

**Goal:** `POST /analyze`, `GET /features/latest`, and `GET /features/history` work correctly with a running FastAPI server, using DictStore backend and test WAV fixtures.

**Depends On:** S02, S03, S04

**Estimated Time:** 3–4 hours

**Files to Create:**

- `src/ingestion/file.py` — create
- `src/api/routes_analyze.py` — create
- `src/api/routes_features.py` — create
- `src/api/app.py` — create (initial version without WebSocket or mic)
- `tests/test_api.py` — create

**file.py must define:**

```python
def load_chunks(
    path: str,
    sr: int = 22050,
    chunk_samples: int = 44100,
    hop_samples: int = 22050,
) -> Generator[np.ndarray, None, None]:
    ...
```

Yields `np.ndarray` of shape `(44100,)` dtype float32. Last chunk is zero-padded if shorter than `chunk_samples`. Raises `ValueError` if loaded audio is shorter than 0.5 seconds (11025 samples at sr=22050).

**app.py** at this slice has no WebSocket, no mic, no generation. It creates the FastAPI app, includes the two route routers, mounts static files at `/ui` (even if the directory is empty), and instantiates DictStore via `get_store()`.

**routes_analyze.py:** POST /analyze accepts multipart file upload, saves to a temp file using `tempfile.NamedTemporaryFile`, calls `load_chunks()`, extracts features from the first chunk only, stores to hot store, returns FeatureVector as JSON. Returns 422 with appropriate detail on unsupported format or too-short audio.

**routes_features.py:** GET /features/latest reads from store, returns 200 + FeatureVector or 404. GET /features/history reads with limit param (clamp to max 30), returns 200 + array.

**Test cases in tests/test_api.py:**

Use `httpx.AsyncClient(app=app, base_url="http://test")` with `pytest-asyncio`.

1. POST /analyze with `tests/fixtures/440hz_sine_2s.wav` — returns 200 + valid FeatureVector JSON
2. POST /analyze with an empty file — returns 422
3. POST /analyze with a text file (not audio) — returns 422 or 500 (document behavior)
4. GET /features/latest before any POST — returns 404
5. POST /analyze then GET /features/latest — returns the stored FeatureVector
6. POST /analyze twice then GET /features/history — returns array of 2 entries
7. GET /features/history?limit=1 — returns array of 1 entry
8. GET /features/history?limit=999 — returns at most 30 entries

**Testing Strategy:**

- `pytest tests/test_api.py -v` — all 8 tests pass
- Manual: `make run` then `curl -X POST -F "file=@tests/fixtures/440hz_sine_2s.wav" http://localhost:8000/analyze` returns JSON

**Done When:**

- [ ] All 8 API tests pass
- [ ] `POST /analyze` response JSON validates against FeatureVector schema (all required keys present)
- [ ] `GET /features/latest` returns 404 on fresh store
- [ ] `GET /features/history` clamped to 30 max regardless of query param
- [ ] Server starts with `make run` and OpenAPI docs accessible at `http://localhost:8000/docs`

---

### S06: WebSocket Server

**Goal:** The `/ws/features` WebSocket endpoint accepts connections, manages the `ConnectionManager`, and broadcasts JSON messages. Tested with an async WebSocket client.

**Depends On:** S05

**Estimated Time:** 2–3 hours

**Files to Create/Modify:**

- `src/api/websocket.py` — create
- `src/api/app.py` — modify (add WebSocket endpoint, ConnectionManager)
- `tests/test_api.py` — modify (add WebSocket tests)

**websocket.py must define `ConnectionManager`:**

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None: ...
    async def disconnect(self, websocket: WebSocket) -> None: ...
    async def broadcast(self, message: dict) -> None: ...
    async def send_personal(self, websocket: WebSocket, message: dict) -> None: ...
```

`broadcast` must catch `WebSocketDisconnect` per connection and remove stale connections gracefully — it must not raise even if one client drops mid-broadcast.

`app.py` WebSocket route at `/ws/features`:
- Accept connection via `ConnectionManager.connect()`
- Enter a receive loop
- On `ControlMessage` with `action: "start_mic"` — log receipt (mic not wired yet)
- On `ControlMessage` with `action: "stop_mic"` — log receipt
- On `ControlMessage` with `action: "trigger_generation"` — log receipt
- On disconnect — call `ConnectionManager.disconnect()`

Add a test helper endpoint `POST /test/broadcast` that accepts `{"message": {...}}` and calls `manager.broadcast()` — this is used in tests only and should be protected by a check for `DEBUG_MODE=true` environment variable.

**Test cases (append to tests/test_api.py):**

Use `fastapi.testclient.TestClient` for WebSocket testing (synchronous).

9. Connect to `/ws/features` — connection accepted
10. POST to `/test/broadcast` with a FeatureMessage shape — WebSocket client receives the message
11. Send `{"type": "control", "action": "start_mic"}` — no error; server logs receipt
12. Disconnect client — no server error; `active_connections` length decreases

**Testing Strategy:**

- `pytest tests/test_api.py -v -k websocket` — WebSocket tests pass
- Manual: open browser console at `http://localhost:8000/ui`, run `const ws = new WebSocket("ws://localhost:8000/ws/features")`, confirm connection

**Done When:**

- [ ] WebSocket tests 9–12 pass
- [ ] `ConnectionManager.broadcast()` does not raise when a client disconnects mid-broadcast
- [ ] Server handles simultaneous connections without crash (test with 3 concurrent WebSocket clients)
- [ ] `/ws/features` route exists and returns 101 on upgrade request

---

### S07: Web UI (Static Dashboard)

**Goal:** A complete HTML/JS/CSS dashboard renders in the browser, connects to the WebSocket, displays feature data and canvas visualizations, and plays audio when a GenerationMessage arrives. Testable by opening in browser while server runs.

**Depends On:** S06

**Estimated Time:** 4–5 hours

**Files to Create:**

- `ui/index.html` — create
- `ui/app.js` — create
- `ui/style.css` — create

**index.html** structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SonicStore</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>SonicStore</h1>
    <div id="controls">
      <button id="btn-start">Start</button>
      <button id="btn-stop" disabled>Stop</button>
      <span id="status">Disconnected</span>
    </div>
  </header>
  <main>
    <section id="panel-visual">
      <canvas id="canvas-waveform" width="600" height="120"></canvas>
      <div id="feature-dashboard">
        <div>BPM: <span id="val-bpm">--</span></div>
        <div>Key: <span id="val-key">--</span></div>
        <div>Energy: <div id="bar-energy"><div id="bar-fill"></div></div> <span id="val-energy">--</span></div>
        <div>Spectral: <span id="val-spectral">-- Hz</span></div>
        <div>Onset: <span id="val-onset">--</span></div>
      </div>
    </section>
    <section id="panel-chroma">
      <canvas id="canvas-chroma" width="600" height="240"></canvas>
    </section>
    <section id="panel-ai">
      <div id="ai-prompt">Waiting for generation...</div>
      <button id="btn-play" disabled>Play generated clip</button>
      <span id="gen-time"></span>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

**app.js** must implement:

1. `connectWebSocket()` — connects to `ws://localhost:8000/ws/features`, retries on close with exponential backoff starting at 2s, max 30s. Updates `#status` span on connect/disconnect.

2. `onMessage(event)` — parses JSON, dispatches to `handleFeatureMessage(data)` or `handleGenerationMessage(data)` based on `type` field.

3. `handleFeatureMessage(data)` — updates all DOM text spans. Triggers `requestAnimationFrame` to draw waveform and chroma column.

4. `drawWaveform(waveformArray)` — draws `waveform_display` (2048 points) as a line on `#canvas-waveform`. Clear canvas, draw centered line, stroke in white.

5. `drawChromaColumn(chromaArray)` — appends a new column (12 rows) to `#canvas-chroma`. Shift existing pixels left by one column width, draw new rightmost column. Color: HSL where hue=240 (blue) at value 0 → hue=60 (yellow) at value 1. Each row is `canvas.height / 12` pixels tall, each column is `canvas.width / 30` pixels wide (30 columns total history visible).

6. `handleGenerationMessage(data)` — stores `audio_b64` for playback. Updates `#ai-prompt` with the prompt text. Enables `#btn-play`. Updates `#gen-time` with generation time.

7. `playGeneratedAudio(audio_b64)` — decodes base64 to ArrayBuffer. Uses `AudioContext.decodeAudioData()`. Stops previous `AudioBufferSourceNode` if playing. Plays new clip via `AudioBufferSourceNode.start()`.

8. Start button sends `{"type":"control","action":"start_mic"}` via WebSocket. Stop button sends `{"type":"control","action":"stop_mic"}`.

**style.css** — dark theme only. Background `#111`. Text `#eee`. Canvas border `1px solid #333`. No external fonts. Minimal spacing.

**Testing Strategy:**

- Manual only for this slice. There is no automated test for UI rendering.
- Test checklist:
  - Open `http://localhost:8000/ui` — page loads without console errors
  - Status shows "Disconnected" then "Connected"
  - POST a WAV to `/analyze` via curl, then POST to `/test/broadcast` with a FeatureMessage — verify DOM updates in browser
  - POST to `/test/broadcast` with a GenerationMessage containing `audio_b64` of a real WAV — verify Play button enables and audio plays when clicked
  - Disconnect and reconnect — status updates, no browser crash
  - Resize window — no layout breaking

**Done When:**

- [ ] Page loads at `http://localhost:8000/ui` without console errors
- [ ] WebSocket connects and status span shows "Connected"
- [ ] Receiving a FeatureMessage updates all 5 dashboard fields
- [ ] Waveform canvas draws a line (not blank) when waveform_display arrives
- [ ] Chroma canvas populates columns left-to-right on each FeatureMessage
- [ ] GenerationMessage enables Play button and plays audio via AudioContext
- [ ] Reconnect logic fires after server restart (manually tested)

---

### S08: Mic Ingestion

**Goal:** `MicIngestion` captures audio from the system microphone, emits `numpy.ndarray` chunks to a queue at the correct rate, testable without the API layer.

**Depends On:** S01

**Estimated Time:** 2–3 hours

**Files to Create:**

- `src/ingestion/mic.py` — create
- `scripts/test_mic_capture.py` — create (standalone script, not pytest)

**mic.py must define:**

```python
SAMPLE_RATE = 22050
CHUNK_SECONDS = 2.0
HOP_SECONDS = 1.0
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)   # 44100
HOP_SAMPLES = int(SAMPLE_RATE * HOP_SECONDS)       # 22050
CHANNELS = 1
DTYPE = "float32"

class MicIngestion:
    def __init__(self, output_queue: queue.Queue):
        self.output_queue = output_queue
        self._ring_buffer = np.zeros(CHUNK_SAMPLES, dtype=DTYPE)
        self._samples_since_last_hop = 0
        self._stream: sd.InputStream | None = None
        self._running = False

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def _callback(self, indata, frames, time, status) -> None: ...
```

Ring buffer logic: the callback appends `indata` to a rolling `_ring_buffer`. When `_samples_since_last_hop >= HOP_SAMPLES`, emit a copy of `_ring_buffer` (the full 44100-sample window) to the queue and reset `_samples_since_last_hop`. This gives 50% overlap.

`scripts/test_mic_capture.py` is a standalone script that:
1. Creates a MicIngestion with a Queue
2. Starts it
3. Waits for 3 chunks
4. Stops it
5. Prints: chunk count, shape, dtype, min/max values
6. Asserts shape == (44100,) and dtype == float32

This script requires a real microphone. It is run manually, not in CI.

**Testing Strategy:**

- Automated: `pytest` cannot test sounddevice without hardware. This slice has NO pytest tests.
- Manual: run `python scripts/test_mic_capture.py` with a microphone connected. Expected output: 3 chunks, shape (44100,), dtype float32.
- On macOS: first run will prompt for microphone permission. Document this in script output.

**Done When:**

- [ ] `MicIngestion.start()` and `stop()` do not raise on import
- [ ] `scripts/test_mic_capture.py` runs successfully with a microphone
- [ ] Output chunks have shape (44100,) and dtype float32
- [ ] Ring buffer provides overlapping windows (second chunk shares last 22050 samples with first chunk — verify by checking that `chunk[22050:]` of chunk 1 equals `chunk[:22050]` of chunk 2, approximately)
- [ ] `stop()` cleanly closes the sounddevice stream without hanging

---

### S09: Mic Loop (Live Feature Pipeline)

**Goal:** When the UI sends `start_mic`, the server starts capturing mic audio, extracting features, storing them, and broadcasting FeatureMessages over WebSocket — the complete live loop from mic to browser, end-to-end.

**Depends On:** S06 (WebSocket), S08 (Mic Ingestion)

**Estimated Time:** 2–3 hours

**Files to Modify:**

- `src/api/app.py` — modify (add lifespan, mic ingestion task, ControlMessage handling)
- `src/api/websocket.py` — modify (handle start_mic/stop_mic control flow)

**app.py changes:**

1. Add a FastAPI lifespan context manager. On startup: call `get_store()`, instantiate `MicIngestion`, do NOT start mic yet.

2. In the WebSocket route handler, when a `ControlMessage` with `action: "start_mic"` arrives:
   - If mic is not running: call `mic.start()`; set a flag `mic_running = True`
   - Launch an `asyncio.create_task` that runs `mic_loop()`

3. `mic_loop()` is an async function that:
   - Polls `mic.output_queue` with `asyncio.get_event_loop().run_in_executor(None, queue.get, timeout=1.0)`
   - On each chunk: calls `extract_features(chunk)` in executor
   - Calls `store.write_latest(features)` in executor
   - Calls `manager.broadcast({"type": "features", "data": features})`
   - Repeats until `mic_running` is False

4. On `stop_mic` ControlMessage: set `mic_running = False`, call `mic.stop()`.

**Testing Strategy:**

- Manual end-to-end test (requires microphone):
  1. `make run`
  2. Open `http://localhost:8000/ui` in browser
  3. Click Start — microphone permission granted
  4. Speak or play audio near microphone
  5. Verify: BPM, Key, Energy fields update in browser every ~1 second
  6. Verify: Waveform canvas animates
  7. Verify: Chroma heatmap columns shift left as new columns appear
  8. Click Stop — updates cease
  - No pytest for this slice.

**Done When:**

- [ ] `start_mic` ControlMessage starts the mic loop without error
- [ ] FeatureMessages arrive in browser at ~1 per second (hop rate)
- [ ] `stop_mic` ControlMessage stops the mic loop cleanly
- [ ] Server does not crash on mic disconnect mid-loop (test by unplugging headset)
- [ ] `GET /features/latest` returns the most recently extracted features while mic is running

---

### S10: Generation Engine (MusicGen)

**Goal:** The GenerationEngine runs in a background thread, polls the store, builds prompts, calls MusicGen-Small, and broadcasts GenerationMessages over WebSocket. Audio plays in the browser.

**Depends On:** S05 (REST API, for store), S06 (WebSocket broadcast), S03 (Prompt Builder)

**Estimated Time:** 4–6 hours (MusicGen load time is the variable)

**Files to Create/Modify:**

- `src/generation/engine.py` — create
- `src/api/app.py` — modify (wire GenerationEngine to lifespan)
- `tests/test_generation.py` — create (mocked, no GPU required)

**engine.py must define:**

```python
from dataclasses import dataclass

@dataclass
class GeneratedClip:
    audio_b64: str
    prompt: str
    duration_seconds: float
    generation_time_ms: int
    features_snapshot: dict

class GenerationEngine:
    def __init__(
        self,
        store: AbstractStore,
        output_queue: queue.Queue,
        interval: float = 3.0,
        model_name: str = "facebook/musicgen-small",
        duration: int = 10,
    ):
        ...

    def start(self) -> None: ...   # launches background thread
    def stop(self) -> None: ...    # sets stop flag, joins thread
    def _loop(self) -> None: ...   # the thread target
```

`_loop` follows the pseudocode in architecture section 2.5 exactly. The `generate_clip(prompt, duration)` inner function loads the model on first call (lazy load, not at `__init__` time — this is important so the server starts immediately and the model loads in the background thread).

Device selection:
```python
import torch
if torch.cuda.is_available():
    device = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
```

On CUDA only: cast model to float16 after loading.

Audio output: `model.generate([prompt])` returns a tensor of shape `(1, 1, samples)`. Squeeze to 1D, convert to numpy float32. Use `scipy.io.wavfile.write` to a `io.BytesIO` buffer (sample rate 32000 — audiocraft's output rate). Base64-encode the bytes.

**app.py changes for S10:**

In lifespan startup: instantiate `GenerationEngine`. Start it. Create `asyncio.create_task` that polls `generation_engine.output_queue` and broadcasts each `GeneratedClip` as a `GenerationMessage`.

The polling coroutine:
```python
async def generation_broadcast_loop():
    while True:
        try:
            clip = generation_engine.output_queue.get_nowait()
            await manager.broadcast({
                "type": "generation",
                "data": {
                    "audio_b64": clip.audio_b64,
                    "prompt": clip.prompt,
                    "duration_seconds": clip.duration_seconds,
                    "generation_time_ms": clip.generation_time_ms,
                    "features_snapshot": clip.features_snapshot,
                }
            })
        except queue.Empty:
            await asyncio.sleep(0.5)
```

**Test cases in tests/test_generation.py:**

Use `monkeypatch` to replace `MusicGen.get_pretrained` with a mock that returns an object whose `generate()` method returns a fixed silence tensor of shape `(1, 1, 320000)`.

1. Engine starts without raising
2. When store has no features, engine loops without producing output
3. When store has a feature vector, engine calls `build_prompt` and produces a `GeneratedClip` in the output queue within `interval + 1` seconds
4. `GeneratedClip.audio_b64` is a non-empty string
5. `GeneratedClip.prompt` is a non-empty string containing "instrumental"
6. Engine stops cleanly when `stop()` is called

**Testing Strategy:**

- `pytest tests/test_generation.py -v` — all 6 mocked tests pass (no GPU required)
- Manual: `make run` with a WAV already POSTed to `/analyze`. Wait `GENERATION_INTERVAL` seconds. Browser should receive GenerationMessage and enable Play button.
- `scripts/benchmark_generation.py` — create this script to time `model.generate()` for one clip and print the wall time. Useful before hackathon to confirm hardware is within budget.

**Done When:**

- [ ] All 6 mocked tests in test_generation.py pass
- [ ] Server starts and logs "Model loading..." in background thread (lazy load message)
- [ ] Model load completes without crashing (first run downloads ~600MB; cached runs in ~5s)
- [ ] After POSTing a WAV and waiting `GENERATION_INTERVAL * 2` seconds, browser receives a GenerationMessage
- [ ] Browser plays the generated audio without error when Play button clicked
- [ ] `benchmark_generation.py` reports generation time within hardware budget (M3 Max <6s, RTX 4080 <4s)

---

### S11: Polish + Demo Mode

**Goal:** Error handling is robust, the UI communicates model-loading state, a "demo mode" pre-loads audio so the demo runs without a live mic if needed, and all edge cases are covered.

**Depends On:** S09 (live mic loop), S10 (generation engine)

**Estimated Time:** 3–4 hours

**Files to Create/Modify:**

- `src/api/app.py` — modify (error handling, startup status endpoint)
- `ui/app.js` — modify (model loading state, error display, demo mode)
- `ui/index.html` — modify (demo mode button, status messages)
- `ui/style.css` — modify (status colors, loading animation)
- `scripts/demo_loader.py` — create (pre-loads a set of WAV files into the store via POST /analyze)

**Error handling additions:**

1. Wrap `extract_features()` call in the mic loop with try/except. On failure, broadcast an `ErrorMessage` with `code: "extraction_failed"`.

2. Wrap `mic.start()` with try/except `sounddevice.PortAudioError`. On failure, broadcast `ErrorMessage` with `code: "mic_unavailable"` and message "Grant microphone permission in System Settings".

3. Wrap `generate_clip()` with try/except. On failure, log the error to stdout and skip this generation cycle (do not crash the thread).

4. Add `GET /status` endpoint:
```json
{
  "store": "redis" | "dict",
  "model_loaded": true | false,
  "mic_running": true | false,
  "connections": 3,
  "features_count": 42
}
```

**UI additions:**

1. On connect, fetch `GET /status`. If `model_loaded` is false, show "Model loading..." banner in the AI section with a pulsing CSS animation. Poll `/status` every 3s until `model_loaded` is true.

2. `handleErrorMessage(data)` — display error code and message in a `#error-banner` div above the main panel. Auto-dismiss after 5 seconds.

3. Demo mode button `[Demo]` in the header. When clicked, calls `scripts/demo_loader.py` via... actually, the browser cannot call a script. Instead, add `POST /demo/start` endpoint in app.py that runs `demo_loader` logic inline: loads 5 pre-selected WAV files from a `demo/` directory (if it exists), POSTs them one by one to `/analyze` with 500ms delays. Respond 404 if `demo/` directory not found.

4. Create `demo/` directory with a note: "Place 5 WAV files here for demo mode (e.g., drum_loop.wav, chord_progression.wav, melody.wav, bass_line.wav, ambient.wav)."

**scripts/demo_loader.py** as standalone script (also invokable from command line):
```
python scripts/demo_loader.py --dir demo/ --interval 0.5
```
Uses `httpx` to POST each file in the directory to `http://localhost:8000/analyze`.

**Testing Strategy:**

- Manual testing only for this slice.
- Test checklist:
  - `/status` returns correct JSON
  - "Model loading..." banner appears on page load, disappears when model is ready
  - Intentional mic failure (revoke permission): `ErrorMessage` appears in UI
  - `POST /demo/start` with `demo/` directory populated: features update in UI
  - `POST /demo/start` with no `demo/` directory: returns 404
  - Server restart followed by browser refresh: UI reconnects, no stale state

**Done When:**

- [ ] `GET /status` returns correct model_loaded and mic_running flags
- [ ] UI shows "Model loading..." banner until model is ready
- [ ] ErrorMessages appear in browser without crashing the UI
- [ ] `POST /demo/start` works when `demo/` directory is populated
- [ ] `make run` starts cleanly and the demo can be shown without a microphone (demo mode)
- [ ] All previous slice tests still pass: `make test` exits 0

---

## 4. Pre-Hackathon Build Schedule

**Window:** April 16 – June 5 (7 weeks)
**Target velocity:** ~7 focused hours/week (1 hour/day weekdays)
**Total estimated work:** 42–55 hours
**Buffer weeks:** 1 week (June 1–5)

### Week 1 (April 16–22): Foundation
**Goal:** Environment working, features extracting, prompts building.

| Day | Task | Slice |
|-----|------|-------|
| Wed Apr 16 | S01: Project scaffolding, requirements.txt, Makefile, fixtures | S01 |
| Thu Apr 17 | S01 finish + S02 start: key_detection.py, normalization.py | S01, S02 |
| Fri Apr 18 | S02 finish: engine.py, test_features.py all passing | S02 |
| Sat Apr 19 | S03: prompt.py, test_prompt.py all passing | S03 |
| Sun Apr 20 | S04: base.py, dict_store.py, redis_store.py, tests | S04 |

**Week 1 exit criteria:** `make test` passes all tests. Feature extraction works on all 3 fixtures. Prompt builder tested. Store layer tested. MusicGen not yet installed (saves time on first week).

---

### Week 2 (April 23–29): API Layer
**Goal:** REST API tested, WebSocket working.

| Day | Task | Slice |
|-----|------|-------|
| Mon Apr 23 | S05 start: file.py, routes_analyze.py | S05 |
| Tue Apr 24 | S05 finish: routes_features.py, app.py, test_api.py | S05 |
| Wed Apr 25 | S06: websocket.py, ConnectionManager, WebSocket tests | S06 |
| Thu Apr 26 | S06 finish + manual WebSocket test in browser | S06 |
| Fri Apr 27 | Buffer / catch-up on Week 1–2 | — |

**Week 2 exit criteria:** `curl -X POST` to `/analyze` returns valid FeatureVector. WebSocket connects from browser. All tests passing.

---

### Week 3 (April 30 – May 6): UI + Mic
**Goal:** Browser dashboard rendering, mic capture working.

| Day | Task | Slice |
|-----|------|-------|
| Mon Apr 28 | S07 start: index.html, style.css | S07 |
| Tue Apr 29 | S07: app.js — WebSocket connect, DOM updates | S07 |
| Wed Apr 30 | S07: Canvas waveform + chroma heatmap rendering | S07 |
| Thu May 1 | S07 finish + S08 start: mic.py | S07, S08 |
| Fri May 2 | S08 finish: test_mic_capture.py manual test | S08 |

**Week 3 exit criteria:** Dashboard renders in browser. Chroma heatmap, waveform, and feature values update when manually broadcasting test data. Mic capture emits chunks of correct shape.

---

### Week 4 (May 7–13): Live Loop
**Goal:** Mic to browser working end-to-end. Real-time feature display while speaking/playing.

| Day | Task | Slice |
|-----|------|-------|
| Mon May 5 | S09: mic_loop in app.py, lifespan task | S09 |
| Tue May 6 | S09: test with microphone — features streaming live | S09 |
| Wed May 7 | S09 finish + MusicGen install begins | S09, S10 setup |
| Thu May 8 | S10 start: engine.py, mocked tests | S10 |
| Fri May 9 | S10: MusicGen load test — confirm model downloads and loads | S10 |

**Week 4 exit criteria:** Live mic → browser working. Speaking near mic updates BPM, energy, chroma in real-time. MusicGen installed and loads (even if generation not yet wired to UI).

---

### Week 5 (May 14–20): Generation + Integration
**Goal:** Full loop working: mic → features → prompt → generate → play.

| Day | Task | Slice |
|-----|------|-------|
| Mon May 12 | S10: generation loop wired to store and WebSocket | S10 |
| Tue May 13 | S10: GenerationMessage broadcast, UI plays audio | S10 |
| Wed May 14 | S10: benchmark_generation.py — measure latency | S10 |
| Thu May 15 | S10 finish: all mocked tests passing | S10 |
| Fri May 16 | Full end-to-end test: mic → play AI response | S10 |

**Week 5 exit criteria:** Full loop demonstrated. Play near mic for 10 seconds, wait for generation, hear AI response. Latency measured and within budget on target hardware.

---

### Week 6 (May 21–27): Polish
**Goal:** S11 complete. Demo mode works without mic. Error states handled gracefully.

| Day | Task | Slice |
|-----|------|-------|
| Mon May 19 | S11: error handling (extraction, mic permission, generation) | S11 |
| Tue May 20 | S11: GET /status + UI model loading banner | S11 |
| Wed May 21 | S11: POST /demo/start + demo_loader.py | S11 |
| Thu May 22 | S11: demo directory with 5 audio files selected | S11 |
| Fri May 23 | S11 finish: full demo run without mic — confirm clean | S11 |

**Week 6 exit criteria:** Demo runs cleanly without a microphone using demo mode. Model loading state is visible. Error messages display without crashing UI.

---

### Week 7 (May 28 – June 4): Rehearsal + Hardening
**Goal:** Run the demo 10 times. Fix every rough edge. Prepare for hackathon transport.

| Day | Task |
|-----|------|
| Wed May 28 | Full demo run on MacBook, time every step |
| Thu May 29 | Full demo run on RTX 4080 laptop if available |
| Fri May 30 | Fix any failures from dry runs |
| Sat May 31 | Tune GENERATION_INTERVAL for best demo feel |
| Sun Jun 1 | Pre-cache MusicGen model: confirm ~/.cache populated |
| Mon Jun 2 | Record fallback demo video (30s screen capture of full loop) |
| Tue Jun 3 | Dry run: present to someone who hasn't seen it |
| Wed Jun 4 | Pack equipment. README final pass. Git tag v1.0.0-demo. |
| Thu Jun 5 | Travel day / rest |

**Week 7 exit criteria:** Demo runs 10 times without failure. Fallback video recorded. Model cache confirmed. Git tagged.

---

## 5. Hackathon Day Plan (June 6–7)

### What Is Already Built and Tested

Everything in S01–S11 is complete before arrival:

- All Python source files, all tests passing
- MusicGen model cached locally (no download needed on-site)
- Demo audio files in `demo/` directory
- README with setup instructions
- Fallback demo video recorded

### What Gets Done On-Site

The 48 hours is NOT for building. It is for:

1. **Hardware setup and verification (June 6 morning, ~2 hours)**
   - Confirm Python env activates on hackathon machine
   - `make install` if needed (all packages pre-installed in venv, just confirm)
   - Run `make test` — all green
   - Launch server, open browser, run demo mode once
   - Confirm MusicGen generates a clip end-to-end

2. **Demo tuning (June 6 afternoon, ~3 hours)**
   - Tune `GENERATION_INTERVAL` based on hardware speed
   - Select the best 5 demo audio files for demo mode
   - Adjust UI text/colors for readability in hackathon room lighting
   - Prepare a compelling 2-minute demo script

3. **Demo rehearsal (June 6 evening, ~2 hours)**
   - Run full demo 5 times with demo script
   - Time each run — target 2-minute clean demo
   - Test presenting with and without microphone

4. **Buffer time (June 7 morning, ~4 hours)**
   - Fix any issues found during rehearsal
   - Prepare submission description (project name, one-liner, what it does)
   - Screenshots for submission

5. **Presentation (June 7 afternoon/evening)**
   - Live demo with microphone
   - Fallback to demo mode if mic fails
   - Fallback to recorded video if demo mode fails

### Demo Rehearsal Schedule

| Time | Activity |
|------|----------|
| Jun 6 09:00 | Arrive, hardware setup, server up |
| Jun 6 11:00 | First full demo run (solo) |
| Jun 6 14:00 | Tuning session — GENERATION_INTERVAL, audio selection |
| Jun 6 16:00 | Demo rehearsal run #1 with another person watching |
| Jun 6 18:00 | Demo rehearsal run #2, incorporate feedback |
| Jun 6 20:00 | Final run before sleep |
| Jun 7 09:00 | Morning run — confirm nothing broke overnight |
| Jun 7 11:00 | Final polish if needed |
| Jun 7 14:00 | Presentations begin |

### Fallback Plan (in priority order)

**Fallback 1 — Mic fails (most likely)**
- Switch to Demo Mode (`POST /demo/start`)
- Pre-loaded audio files cycle through the feature extractor
- Everything else works identically
- Audience sees the same UI, same chroma heatmap, same generation

**Fallback 2 — Generation too slow on hackathon hardware**
- Set `MUSICGEN_DURATION=5` (halves generation time)
- Set `GENERATION_INTERVAL=5.0` (reduces pressure)
- Live feature display still works perfectly
- Acknowledge "generation running in background" to judges

**Fallback 3 — MusicGen crashes (low probability)**
- Comment out GenerationEngine startup in app.py
- Demo becomes "Real-time MIR feature store" without the generation loop
- Feature extraction, WebSocket streaming, visual dashboard all still demo perfectly
- Honest framing: "Generation is one of four components; this is the MIR core"

**Fallback 4 — Server crashes entirely**
- Play the recorded 30-second screen capture video
- Explain architecture from the architecture diagram
- Code is on GitHub, judges can verify it's real

---

## 6. Testing Strategy Per Slice

| Slice | Test Method | Test Fixture | Command |
|-------|-------------|--------------|---------|
| S01 | Manual: import check, fixture generation | None | `python scripts/generate_test_audio.py` |
| S02 | pytest unit tests | `tests/fixtures/440hz_sine_2s.wav`, `silence_2s.wav`, `chirp_2s.wav` | `pytest tests/test_features.py -v` |
| S03 | pytest unit tests | Hardcoded dicts in test file | `pytest tests/test_prompt.py -v` |
| S04 | pytest unit (dict) + integration (Redis) | None (instantiated directly) | `pytest tests/test_store.py -m "not integration"` |
| S05 | pytest async (httpx TestClient) | `tests/fixtures/440hz_sine_2s.wav` | `pytest tests/test_api.py -v` |
| S06 | pytest (WebSocket via TestClient) + manual browser | None | `pytest tests/test_api.py -v -k websocket` |
| S07 | Manual browser checklist | Server must be running | Open `http://localhost:8000/ui` |
| S08 | Manual: `scripts/test_mic_capture.py` | Real microphone | `python scripts/test_mic_capture.py` |
| S09 | Manual end-to-end | Real microphone + running server | Manual: click Start, speak, observe UI |
| S10 | pytest mocked (monkeypatch) + manual E2E | Mocked tensor / WAV file | `pytest tests/test_generation.py -v` |
| S11 | Manual checklist | `demo/` directory with WAV files | Manual: full demo run |

**Master test command (runs all automatable tests):**

```bash
make test
# Equivalent to:
pytest tests/ -v -m "not integration"
```

**Integration test command (requires Redis):**

```bash
make redis-up && pytest tests/ -v
```

---

## 7. Risk-Ordered Priority

### Tier 1: Must Have for Demo (Core Value Proposition)

If these are not working on June 7, the demo is not viable:

| Slice | Why It's Tier 1 |
|-------|----------------|
| S02 Feature Engine | The entire product is "MIR feature extraction" — this is the product |
| S05 REST API | Needed to ingest audio and return features |
| S06 WebSocket | Needed for real-time display |
| S07 Web UI | Judges need to see something running |
| S10 Generation Engine | The "feedback loop" is half the story; demo without it is a feature extractor |

### Tier 2: Important for Demo Quality

Missing these hurts the demo but doesn't kill it:

| Slice | Fallback if Cut |
|-------|----------------|
| S08 Mic Ingestion | Use Demo Mode (POST /demo/start) with pre-loaded audio |
| S09 Mic Loop | Use Demo Mode |
| S11 Polish + Demo Mode | Demo works but may crash on edge cases |

### Tier 3: Nice to Have

These improve robustness but judges won't miss them:

| Slice | Fallback if Cut |
|-------|----------------|
| S04 RedisStore (the Redis half) | DictStore fallback is seamless and invisible to judges |
| S01 Makefile completeness | Just run uvicorn directly |

### If Time Runs Out: Minimum Viable Demo

If the hackathon arrives and only slices S01–S07 are complete (no mic, no MusicGen):

The demo is still compelling as "Real-time MIR feature store with WebSocket streaming." Use `POST /analyze` from curl during the demo. Narrate the generation loop as architecture ("this is what MusicGen receives"). This is a 70% demo, not a failure.

---

## 8. Deferred Work (Not This Roadmap)

The following are explicitly outside the scope of the v1 hackathon build. Do not implement or stub them.

| Item | Reason for Deferral |
|------|---------------------|
| RAVE real-time tier (<50ms) | Requires C++/Rust FFI; Decision 1 deferred |
| Multi-model entanglement (Model A + Model B) | Agentic Prosthetic north star; not v1 scope |
| SonicStore "intuition" / surprise mechanisms | North star; not v1 scope |
| Haptic / somatic body interface | North star; not v1 scope |
| Essentia feature extraction | librosa covers all v1 needs |
| MLX port of MusicGen | May outperform on M3 Max; evaluate post-hackathon |
| MIDI output | Audio only per architecture spec |
| Streaming generation (chunk-by-chunk) | Generate-then-play per architecture spec |
| Docker / containerization | Local install is sufficient |
| Multi-user / authentication | Single user, local machine |
| Cloud deployment | Local-only per Decision 1 |
| DuckDB / SQLite persistent storage | Redis or dict store only |
| Fine-tuning or training | Inference only |
| DAW plugin (VST/AU) | Separate product |
| Chart.js or D3 in the UI | Vanilla Canvas only |
| Mobile browser support | Desktop Chrome/Firefox only |
| Multiple concurrent MusicGen instances | One model only |

---

## 9. Sequence Rules

1. Complete each slice fully — all tests passing — before starting the next.
2. No partial slice work carried forward. A slice is either done or not started.
3. If blocked (import error, hardware issue, sounddevice issue): document the blocker and continue with a non-blocked slice. Do not skip ahead on dependent slices.
4. S08 (Mic Ingestion) has no pytest tests and is hardware-dependent. It may be started in parallel with S07 (Web UI) since they share no dependencies.
5. S10 (Generation Engine) has the highest time variance due to MusicGen download and load time. Begin the MusicGen install process at the end of Week 3 even if S10 itself starts in Week 4.
6. No new slices or features added to the roadmap without explicit approval. All additions must be scoped and placed in the sequence.

---

*Roadmap by: Technical Director*
*For: Danny (Composer) — Single developer build*
*Status: Ready. S01 starts today, April 16.*
