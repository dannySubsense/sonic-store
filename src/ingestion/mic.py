"""Microphone audio ingestion via sounddevice; emits numpy chunks to a queue."""

import queue
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 22050
CHUNK_SECONDS = 2.0
HOP_SECONDS = 1.0
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_SECONDS)  # 44100
HOP_SAMPLES = int(SAMPLE_RATE * HOP_SECONDS)       # 22050
CHANNELS = 1
DTYPE = "float32"


class MicIngestion:
    """Capture mic chunks via sounddevice and push numpy arrays to an output queue.

    Output contract: np.ndarray float32 shape (44100,), values in [-1.0, 1.0].
    Uses a ring buffer with 50% overlap (2s window, 1s hop).
    """

    def __init__(self, output_queue: Optional[queue.Queue] = None) -> None:
        self.output_queue: queue.Queue[np.ndarray] = output_queue or queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._ring_buffer: np.ndarray = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
        self._write_pos: int = 0
        self._samples_since_hop: int = 0
        self._running: bool = False

    def start(self) -> None:
        """Open the sounddevice input stream and begin accumulating chunks."""
        if self._running:
            return
        self._running = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()
        print(f"[mic] Started (sr={SAMPLE_RATE}, chunk={CHUNK_SECONDS}s, hop={HOP_SECONDS}s)")

    def stop(self) -> None:
        """Close the input stream cleanly."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[mic] Stopped")

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """sounddevice callback; accumulates samples into ring buffer, emits on hop."""
        if status:
            print(f"[mic] sounddevice status: {status}")

        # indata shape is (frames, channels); squeeze to 1D
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()

        for sample in mono:
            self._ring_buffer[self._write_pos] = sample
            self._write_pos = (self._write_pos + 1) % CHUNK_SAMPLES
            self._samples_since_hop += 1

            if self._samples_since_hop >= HOP_SAMPLES:
                # Emit a copy of the ring buffer, reordered so it's contiguous
                chunk = np.roll(self._ring_buffer, -self._write_pos).copy()
                self.output_queue.put(chunk)
                self._samples_since_hop = 0
