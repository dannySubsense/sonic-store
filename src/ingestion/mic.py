"""Microphone audio ingestion via sounddevice; emits numpy chunks to a queue."""

import queue
from typing import Optional

import numpy as np

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
    """

    def __init__(self, output_queue: Optional[queue.Queue] = None) -> None:
        self.output_queue: queue.Queue[np.ndarray] = output_queue or queue.Queue()
        self._stream = None
        self._ring_buffer: np.ndarray = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
        self._samples_since_hop: int = 0

    def start(self) -> None:
        """Open the sounddevice input stream and begin accumulating chunks."""
        raise NotImplementedError

    def stop(self) -> None:
        """Close the input stream and flush the ring buffer."""
        raise NotImplementedError

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """sounddevice callback; accumulates samples and enqueues complete windows."""
        raise NotImplementedError
