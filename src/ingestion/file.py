"""File-based audio ingestion: load via librosa and yield fixed-size chunks."""

from typing import Generator

import librosa
import numpy as np

SAMPLE_RATE = 22050
CHUNK_SAMPLES = int(SAMPLE_RATE * 2.0)  # 44100
HOP_SAMPLES = int(SAMPLE_RATE * 1.0)    # 22050
MIN_SAMPLES = int(SAMPLE_RATE * 0.5)    # 11025


def load_and_chunk(
    path: str,
    sr: int = SAMPLE_RATE,
    chunk_samples: int = CHUNK_SAMPLES,
    hop_samples: int = HOP_SAMPLES,
) -> Generator[np.ndarray, None, None]:
    """Load audio file and yield overlapping float32 chunks of shape (chunk_samples,).

    Uses 50% overlap (2s window, 1s hop). Pads final chunk with zeros if needed.
    Raises ValueError if audio is shorter than 0.5s.
    """
    audio, _ = librosa.load(path, sr=sr, mono=True)
    audio = audio.astype(np.float32)

    if len(audio) < MIN_SAMPLES:
        raise ValueError(
            f"Audio too short: {len(audio)} samples ({len(audio)/sr:.2f}s), "
            f"minimum is {MIN_SAMPLES} samples (0.5s)"
        )

    offset = 0
    while offset < len(audio):
        chunk = audio[offset : offset + chunk_samples]
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)), mode="constant")
        yield chunk
        offset += hop_samples
