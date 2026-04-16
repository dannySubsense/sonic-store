"""File-based audio ingestion: load via librosa and yield fixed-size chunks."""

from typing import Generator

import numpy as np

SAMPLE_RATE = 22050
CHUNK_SAMPLES = int(SAMPLE_RATE * 2.0)  # 44100
HOP_SAMPLES = int(SAMPLE_RATE * 1.0)    # 22050


def load_and_chunk(path: str) -> Generator[np.ndarray, None, None]:
    """Load audio file and yield overlapping float32 chunks of shape (44100,).

    Uses 50% overlap (2s window, 1s hop). Pads final chunk with zeros if needed.
    """
    raise NotImplementedError
