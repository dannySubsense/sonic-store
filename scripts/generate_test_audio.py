"""Generate a 2-second 440 Hz sine wave WAV file for offline testing."""

import os

import numpy as np
import scipy.io.wavfile

SAMPLE_RATE = 22050
DURATION_SECONDS = 2.0
FREQUENCY_HZ = 440.0
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "tests", "fixtures", "440hz_sine_2s.wav"
)


def generate_sine_wav(
    frequency: float = FREQUENCY_HZ,
    duration: float = DURATION_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    output_path: str = OUTPUT_PATH,
) -> str:
    """Write a mono float32 sine wave WAV and return the output path."""
    n_samples = int(sample_rate * duration)
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, sample_rate, audio)
    print(f"Written: {os.path.abspath(output_path)}  ({n_samples} samples @ {sample_rate} Hz)")
    return output_path


if __name__ == "__main__":
    generate_sine_wav()
