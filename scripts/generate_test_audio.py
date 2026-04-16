"""Generate test audio WAV fixtures for offline testing."""

import os

import numpy as np
import scipy.io.wavfile

SAMPLE_RATE = 22050
DURATION_SECONDS = 2.0
FREQUENCY_HZ = 440.0

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")


def generate_sine_wav(
    frequency: float = FREQUENCY_HZ,
    duration: float = DURATION_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    output_path: str = None,
) -> str:
    """Write a mono float32 sine wave WAV and return the output path."""
    if output_path is None:
        output_path = os.path.join(FIXTURES_DIR, "440hz_sine_2s.wav")
    n_samples = int(sample_rate * duration)
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, sample_rate, audio)
    print(f"Written: {os.path.abspath(output_path)}  ({n_samples} samples @ {sample_rate} Hz)")
    return output_path


def generate_silence_wav(
    duration: float = DURATION_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    output_path: str = None,
) -> str:
    """Write a mono float32 silence WAV and return the output path."""
    if output_path is None:
        output_path = os.path.join(FIXTURES_DIR, "silence_2s.wav")
    n_samples = int(sample_rate * duration)
    audio = np.zeros(n_samples, dtype=np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, sample_rate, audio)
    print(f"Written: {os.path.abspath(output_path)}  ({n_samples} samples @ {sample_rate} Hz)")
    return output_path


def generate_chirp_wav(
    f0: float = 200.0,
    f1: float = 2000.0,
    duration: float = DURATION_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    output_path: str = None,
) -> str:
    """Write a mono float32 linear frequency sweep (chirp) WAV and return the output path."""
    if output_path is None:
        output_path = os.path.join(FIXTURES_DIR, "chirp_2s.wav")
    n_samples = int(sample_rate * duration)
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    audio = np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * duration) * t ** 2)).astype(np.float32)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, sample_rate, audio)
    print(f"Written: {os.path.abspath(output_path)}  ({n_samples} samples @ {sample_rate} Hz)")
    return output_path


if __name__ == "__main__":
    generate_sine_wav()
    generate_silence_wav()
    generate_chirp_wav()
