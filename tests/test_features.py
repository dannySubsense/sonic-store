"""Unit tests for extract_features using synthetic sine wave audio."""

import numpy as np
import pytest

from src.features.engine import extract_features


SAMPLE_RATE = 22050
CHUNK_SAMPLES = 44100  # 2 seconds


def make_sine(freq: float = 440.0, duration_samples: int = CHUNK_SAMPLES) -> np.ndarray:
    """Generate a float32 sine wave normalized to [-1, 1]."""
    t = np.arange(duration_samples, dtype=np.float32) / SAMPLE_RATE
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


@pytest.fixture
def sine_440() -> np.ndarray:
    return make_sine(440.0)


def test_extract_features_returns_dict(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    assert isinstance(result, dict)


def test_chroma_shape_and_range(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    chroma = result["chroma"]
    assert len(chroma) == 12, f"Expected 12 chroma bins, got {len(chroma)}"
    assert all(isinstance(v, float) for v in chroma)
    assert all(0.0 <= v <= 1.0 for v in chroma), f"Chroma values out of range: {chroma}"


def test_bpm_is_non_negative_float(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    bpm = result["bpm"]
    assert isinstance(bpm, float)
    # A pure sine has no rhythmic onsets; librosa may return 0.0. Ensure >= 0.
    assert bpm >= 0.0, f"BPM should be non-negative, got {bpm}"


def test_key_pitch_class_and_mode(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    pitch_class = result["key_pitch_class"]
    mode = result["key_mode"]
    assert isinstance(pitch_class, int)
    assert 0 <= pitch_class <= 11, f"pitch_class out of range: {pitch_class}"
    assert mode in ("major", "minor"), f"mode must be 'major' or 'minor', got {mode!r}"


def test_rms_energy_range(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    rms = result["rms_energy"]
    assert isinstance(rms, float)
    assert 0.0 <= rms <= 1.0, f"rms_energy out of [0, 1]: {rms}"


def test_spectral_centroid_reasonable(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    sc = result["spectral_centroid_hz"]
    assert isinstance(sc, float)
    # For a 440 Hz sine, centroid should be near 440 Hz
    assert 100.0 <= sc <= 5000.0, f"spectral_centroid_hz implausible: {sc}"


def test_onset_strength_range(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    onset = result["onset_strength"]
    assert isinstance(onset, float)
    assert 0.0 <= onset <= 1.0, f"onset_strength out of [0, 1]: {onset}"


def test_mel_spectrogram_shape(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    mel = result["mel_spectrogram"]
    assert isinstance(mel, list)
    assert len(mel) == 128, f"mel_spectrogram should have 128 rows, got {len(mel)}"
    assert len(mel[0]) > 0, "mel_spectrogram time frames should not be empty"


def test_waveform_display_length(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    wd = result["waveform_display"]
    assert len(wd) == 2048, f"waveform_display should be 2048 points, got {len(wd)}"


def test_all_required_keys_present(sine_440: np.ndarray) -> None:
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    required = {
        "timestamp", "chunk_index", "source", "duration_seconds",
        "chroma", "bpm", "key_pitch_class", "key_mode",
        "rms_energy", "spectral_centroid_hz", "onset_strength",
        "mel_spectrogram", "waveform_display",
    }
    missing = required - result.keys()
    assert not missing, f"Missing keys: {missing}"


def test_440hz_chroma_peak_near_A(sine_440: np.ndarray) -> None:
    """440 Hz is A4; chroma peak should be at index 9 (A)."""
    result = extract_features(sine_440, sr=SAMPLE_RATE)
    chroma = result["chroma"]
    dominant_pitch = int(np.argmax(chroma))
    # Allow A (9) or adjacent pitch classes due to CQT resolution
    assert abs(dominant_pitch - 9) <= 1 or dominant_pitch in (9,), (
        f"440Hz should peak near pitch class 9 (A), got {dominant_pitch}"
    )
