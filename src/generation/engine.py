"""Generation engine: background thread reads feature store and runs MusicGen inference."""

import base64
import io
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from src.generation.prompt import build_prompt

FeatureVector = Dict[str, Any]

GENERATION_INTERVAL = float(os.getenv("GENERATION_INTERVAL", "3.0"))
MUSICGEN_MODEL = os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small")
MUSICGEN_DURATION = int(os.getenv("MUSICGEN_DURATION", "10"))


@dataclass
class GeneratedClip:
    """Container for a generated audio clip and its metadata."""

    audio_b64: str
    prompt: str
    duration_seconds: float
    generation_time_ms: int
    features_snapshot: FeatureVector


class GenerationEngine:
    """Background thread: poll feature store, build prompt, run MusicGen, emit clips.

    Communicates with the FastAPI process via a thread-safe output_queue.
    Model is loaded lazily on the first generation cycle (not at __init__ time)
    so the server starts immediately.
    """

    def __init__(
        self,
        store: Any,
        output_queue: Optional[queue.Queue] = None,
        interval: float = GENERATION_INTERVAL,
        model_name: str = MUSICGEN_MODEL,
        duration: int = MUSICGEN_DURATION,
    ) -> None:
        self._store = store
        self.output_queue: queue.Queue[GeneratedClip] = output_queue or queue.Queue()
        self._interval = interval
        self._model_name = model_name
        self._duration = duration
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._model = None  # MusicGen loaded lazily in background thread
        self._device: Optional[str] = None
        self.model_loaded = False
        self._last_generated_timestamp: Optional[int] = None

    def start(self) -> None:
        """Launch the background generation thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._generation_loop,
            name="generation-engine",
            daemon=True,
        )
        self._thread.start()
        print("[generation] Background thread started")

    def stop(self) -> None:
        """Signal the background thread to exit and join it."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=15.0)
            self._thread = None
        print("[generation] Background thread stopped")

    def _select_device(self) -> str:
        """Choose best available device: CUDA > MPS > CPU."""
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self) -> None:
        """Load MusicGen-Small from pretrained weights (downloads on first run)."""
        import torch
        from audiocraft.models import MusicGen

        self._device = self._select_device()
        print(f"[generation] Loading model {self._model_name} on {self._device}...")

        model = MusicGen.get_pretrained(self._model_name)
        model.set_generation_params(
            duration=self._duration,
            use_sampling=True,
            top_k=250,
            temperature=1.0,
        )

        # FP16 on CUDA only — MPS is unstable with FP16 for audiocraft
        if self._device == "cuda":
            model = model.half()

        self._model = model
        self.model_loaded = True
        print(f"[generation] Model loaded on {self._device}")

    def _generation_loop(self) -> None:
        """Background thread main loop: poll store, build prompt, generate, enqueue."""
        # Lazy-load the model on first iteration
        try:
            self._load_model()
        except Exception as e:
            print(f"[generation] Failed to load model: {e}")
            self._running = False
            return

        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break

            try:
                features = self._store.get_latest()
                if features is None:
                    continue

                # Skip if we already generated for this timestamp
                ts = features.get("timestamp")
                if ts is not None and ts == self._last_generated_timestamp:
                    continue

                prompt = build_prompt(features)
                clip = self._generate_clip(prompt, features)
                self.output_queue.put(clip)
                self._last_generated_timestamp = ts

            except Exception as e:
                print(f"[generation] Error in generation loop: {e}")
                continue

    def _generate_clip(self, prompt: str, features: FeatureVector) -> GeneratedClip:
        """Run MusicGen inference; return GeneratedClip with base64-encoded WAV."""
        import torch
        import scipy.io.wavfile as wavfile

        start_time = time.time()

        with torch.no_grad():
            output = self._model.generate([prompt])  # shape (1, 1, samples)

        # Squeeze to 1D numpy float32
        audio_tensor = output.squeeze().cpu()
        audio_np = audio_tensor.numpy().astype(np.float32)

        # Encode as WAV bytes (audiocraft output is 32kHz)
        buf = io.BytesIO()
        wavfile.write(buf, 32000, audio_np)
        audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        elapsed_ms = int((time.time() - start_time) * 1000)
        duration_seconds = len(audio_np) / 32000.0

        print(f"[generation] Generated {duration_seconds:.1f}s clip in {elapsed_ms}ms")

        return GeneratedClip(
            audio_b64=audio_b64,
            prompt=prompt,
            duration_seconds=duration_seconds,
            generation_time_ms=elapsed_ms,
            features_snapshot=features,
        )
