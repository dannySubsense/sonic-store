"""Generation engine: background thread reads feature store and runs MusicGen inference."""

import queue
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional


FeatureVector = Dict[str, Any]

GENERATION_INTERVAL = 3.0  # seconds between generation checks


@dataclass
class GeneratedClip:
    """Container for a generated audio clip and its metadata."""

    audio_b64: str
    prompt: str
    duration_seconds: float
    generation_time_ms: float
    features_snapshot: FeatureVector


class GenerationEngine:
    """Background thread: poll feature store, build prompt, run MusicGen, emit clips.

    Communicates with the FastAPI process via a thread-safe output_queue.
    """

    def __init__(
        self,
        store: Any,
        output_queue: Optional[queue.Queue] = None,
        interval: float = GENERATION_INTERVAL,
    ) -> None:
        self._store = store
        self.output_queue: queue.Queue[GeneratedClip] = output_queue or queue.Queue()
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._model = None  # MusicGen loaded lazily

    def start(self) -> None:
        """Launch the background generation thread."""
        raise NotImplementedError

    def stop(self) -> None:
        """Signal the background thread to exit and join it."""
        raise NotImplementedError

    def _load_model(self) -> None:
        """Load MusicGen-Small from pretrained weights (downloads on first run)."""
        raise NotImplementedError

    def _generation_loop(self) -> None:
        """Background thread main loop: poll store, build prompt, generate, enqueue."""
        raise NotImplementedError

    def _generate_clip(self, prompt: str, features: FeatureVector) -> GeneratedClip:
        """Run MusicGen inference; return GeneratedClip with base64-encoded WAV."""
        raise NotImplementedError
