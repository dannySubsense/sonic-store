// SonicStore Web UI — WebSocket client + Canvas rendering

const KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const CHROMA_COLUMNS = 30;

let ws = null;
let reconnectDelay = 2000;
let audioCtx = null;
let currentSource = null;
let currentAudioB64 = null;

// --- DOM refs ---
const statusEl = document.getElementById('status');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnPlay = document.getElementById('btn-play');
const errorBanner = document.getElementById('error-banner');
const valBpm = document.getElementById('val-bpm');
const valKey = document.getElementById('val-key');
const valEnergy = document.getElementById('val-energy');
const valSpectral = document.getElementById('val-spectral');
const valOnset = document.getElementById('val-onset');
const barFill = document.getElementById('bar-fill');
const aiPrompt = document.getElementById('ai-prompt');
const genTime = document.getElementById('gen-time');

const waveformCanvas = document.getElementById('canvas-waveform');
const waveformCtx = waveformCanvas.getContext('2d');
const chromaCanvas = document.getElementById('canvas-chroma');
const chromaCtx = chromaCanvas.getContext('2d');

// --- WebSocket ---

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws/features`);

  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    statusEl.className = 'connected';
    reconnectDelay = 2000;
  };

  ws.onclose = () => {
    statusEl.textContent = 'Disconnected';
    statusEl.className = '';
    setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
      connectWebSocket();
    }, reconnectDelay);
  };

  ws.onerror = () => {
    ws.close();
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case 'features':
          handleFeatureMessage(msg.data);
          break;
        case 'generation':
          handleGenerationMessage(msg.data);
          break;
        case 'error':
          handleErrorMessage(msg);
          break;
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
}

// --- Feature handling ---

function handleFeatureMessage(data) {
  // Update dashboard text
  valBpm.textContent = Math.round(data.bpm);
  valKey.textContent = KEY_NAMES[data.key_pitch_class] + ' ' + data.key_mode;
  valEnergy.textContent = data.rms_energy.toFixed(2);
  valSpectral.textContent = Math.round(data.spectral_centroid_hz) + ' Hz';
  valOnset.textContent = data.onset_strength.toFixed(2);

  // Update energy bar
  barFill.style.width = (data.rms_energy * 100) + '%';

  // Draw canvases
  requestAnimationFrame(() => {
    if (data.waveform_display) {
      drawWaveform(data.waveform_display);
    }
    if (data.chroma) {
      drawChromaColumn(data.chroma);
    }
  });
}

// --- Waveform ---

function drawWaveform(waveformArray) {
  const w = waveformCanvas.width;
  const h = waveformCanvas.height;
  const mid = h / 2;

  waveformCtx.fillStyle = '#111';
  waveformCtx.fillRect(0, 0, w, h);

  waveformCtx.strokeStyle = '#4f4';
  waveformCtx.lineWidth = 1;
  waveformCtx.beginPath();

  const step = w / waveformArray.length;
  for (let i = 0; i < waveformArray.length; i++) {
    const x = i * step;
    const y = mid - (waveformArray[i] * mid);
    if (i === 0) {
      waveformCtx.moveTo(x, y);
    } else {
      waveformCtx.lineTo(x, y);
    }
  }

  waveformCtx.stroke();

  // Center line
  waveformCtx.strokeStyle = '#333';
  waveformCtx.lineWidth = 0.5;
  waveformCtx.beginPath();
  waveformCtx.moveTo(0, mid);
  waveformCtx.lineTo(w, mid);
  waveformCtx.stroke();
}

// --- Chroma heatmap ---

function drawChromaColumn(chromaArray) {
  const w = chromaCanvas.width;
  const h = chromaCanvas.height;
  const colWidth = Math.floor(w / CHROMA_COLUMNS);
  const rowHeight = h / 12;

  // Shift existing content left by one column
  const imageData = chromaCtx.getImageData(colWidth, 0, w - colWidth, h);
  chromaCtx.putImageData(imageData, 0, 0);

  // Clear rightmost column
  chromaCtx.fillStyle = '#111';
  chromaCtx.fillRect(w - colWidth, 0, colWidth, h);

  // Draw new column (index 0 = C at bottom, 11 = B at top)
  for (let i = 0; i < 12; i++) {
    const value = chromaArray[11 - i]; // flip so C is at bottom
    // HSL interpolation: blue (240) at 0 -> yellow (60) at 1
    const hue = 240 - (value * 180);
    const lightness = 15 + (value * 45);
    chromaCtx.fillStyle = `hsl(${hue}, 80%, ${lightness}%)`;
    chromaCtx.fillRect(w - colWidth, i * rowHeight, colWidth, rowHeight);
  }
}

// --- Generation handling ---

function handleGenerationMessage(data) {
  currentAudioB64 = data.audio_b64;
  aiPrompt.textContent = data.prompt;
  btnPlay.disabled = false;
  genTime.textContent = `Generated in ${(data.generation_time_ms / 1000).toFixed(1)}s`;
}

// --- Audio playback ---

function playGeneratedAudio() {
  if (!currentAudioB64) return;

  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }

  // Stop previous playback
  if (currentSource) {
    try { currentSource.stop(); } catch (e) { /* already stopped */ }
  }

  // Decode base64 to ArrayBuffer
  const binaryStr = atob(currentAudioB64);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }

  audioCtx.decodeAudioData(bytes.buffer, (buffer) => {
    currentSource = audioCtx.createBufferSource();
    currentSource.buffer = buffer;
    currentSource.connect(audioCtx.destination);
    currentSource.start();
    currentSource.onended = () => { currentSource = null; };
  }, (err) => {
    console.error('Failed to decode audio:', err);
  });
}

// --- Error handling ---

function handleErrorMessage(msg) {
  errorBanner.textContent = `${msg.code}: ${msg.message}`;
  errorBanner.classList.remove('hidden');
  setTimeout(() => errorBanner.classList.add('hidden'), 5000);
}

// --- Controls ---

btnStart.addEventListener('click', () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'control', action: 'start_mic' }));
    btnStart.disabled = true;
    btnStop.disabled = false;
  }
});

btnStop.addEventListener('click', () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'control', action: 'stop_mic' }));
    btnStart.disabled = false;
    btnStop.disabled = true;
  }
});

btnPlay.addEventListener('click', playGeneratedAudio);

// --- Init ---
connectWebSocket();
