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


def test_silence_rms_energy_and_waveform_display() -> None:
    """Silence: rms_energy < 0.05 and waveform_display has exactly 2048 points."""
    silence = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
    result = extract_features(silence, sr=SAMPLE_RATE)
    assert result["rms_energy"] < 0.05, (
        f"Silence rms_energy should be < 0.05, got {result['rms_energy']}"
    )
    assert len(result["waveform_display"]) == 2048, (
        f"waveform_display should be 2048 points, got {len(result['waveform_display'])}"
    )


def test_chirp_spectral_centroid_above_800hz() -> None:
    """Chirp (200-2000 Hz sweep): spectral_centroid_hz should exceed 800 Hz."""
    t = np.arange(CHUNK_SAMPLES, dtype=np.float32) / SAMPLE_RATE
    f0, f1 = 200.0, 2000.0
    chirp = np.sin(2 * np.pi * (f0 * t + (f1 - f0) / (2 * 2.0) * t**2)).astype(np.float32)
    result = extract_features(chirp, sr=SAMPLE_RATE)
    sc = result["spectral_centroid_hz"]
    assert sc > 800.0, (
        f"Chirp spectral_centroid_hz should be > 800 Hz (broad-spectrum signal), got {sc}"
    )


def test_extraction_wall_time_under_2_seconds(sine_440: np.ndarray) -> None:
    """Feature extraction on the sine fixture must complete in under 2 seconds."""
    import time
    start = time.time()
    extract_features(sine_440, sr=SAMPLE_RATE)
    elapsed = time.time() - start
    print(f"\nextract_features wall time: {elapsed:.3f}s")
    assert elapsed < 2.0, (
        f"extract_features took {elapsed:.3f}s, must be < 2.0s"
    )


# ---------------------------------------------------------------------------
# H1.S02 — Layer 1 Widening tests (12 new tests; AC-01, AC-09)
# ---------------------------------------------------------------------------

NEW_LAYER1_KEYS = [
    "spectral_rolloff_hz",
    "spectral_flux",
    "spectral_contrast",
    "zero_crossing_rate",
    "mfcc",
    "harmonic_ratio",
    "tonnetz",
]

V1_KEYS = [
    "timestamp",
    "chunk_index",
    "source",
    "duration_seconds",
    "chroma",
    "bpm",
    "key_pitch_class",
    "key_mode",
    "rms_energy",
    "spectral_centroid_hz",
    "onset_strength",
    "mel_spectrogram",
    "waveform_display",
]


def test_layer1_new_keys_present(sine_440: np.ndarray) -> None:
    """AC-01: All 7 new Layer 1 keys must be present in the returned dict."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    for key in NEW_LAYER1_KEYS:
        assert key in fv, f"Expected key '{key}' missing from FeatureVector"


def test_spectral_rolloff_hz_range(sine_440: np.ndarray) -> None:
    """AC-01: spectral_rolloff_hz is a float in the range (0.0, 11025.0]."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["spectral_rolloff_hz"]
    assert isinstance(val, float), f"spectral_rolloff_hz must be float, got {type(val)}"
    assert val > 0.0, f"spectral_rolloff_hz must be > 0.0, got {val}"
    assert val <= 11025.0, f"spectral_rolloff_hz must be <= 11025.0 (sr/2), got {val}"


def test_spectral_flux_range(sine_440: np.ndarray) -> None:
    """AC-01: spectral_flux is a float in [0.0, 1.0]."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["spectral_flux"]
    assert isinstance(val, float), f"spectral_flux must be float, got {type(val)}"
    assert val >= 0.0, f"spectral_flux must be >= 0.0, got {val}"
    assert val <= 1.0, f"spectral_flux must be <= 1.0, got {val}"


def test_spectral_contrast_shape(sine_440: np.ndarray) -> None:
    """AC-01: spectral_contrast is a list of exactly 7 floats."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["spectral_contrast"]
    assert isinstance(val, list), f"spectral_contrast must be list, got {type(val)}"
    assert len(val) == 7, f"spectral_contrast must have 7 elements, got {len(val)}"
    assert all(isinstance(x, float) for x in val), (
        f"spectral_contrast elements must all be float, got types: {[type(x) for x in val]}"
    )


def test_spectral_contrast_finite() -> None:
    """AC-01 / OQ-PLAN-02: spectral_contrast contains no NaN or Inf across silence, sine, noise."""
    silence = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
    sine = make_sine(440.0)
    noise = np.random.RandomState(42).randn(CHUNK_SAMPLES).astype(np.float32) * 0.1

    for label, audio in [("silence", silence), ("sine", sine), ("noise", noise)]:
        fv = extract_features(audio, sr=SAMPLE_RATE)
        contrast = fv["spectral_contrast"]
        assert all(np.isfinite(x) for x in contrast), (
            f"spectral_contrast contains NaN/Inf for {label} fixture: {contrast}"
        )


def test_zero_crossing_rate_range(sine_440: np.ndarray) -> None:
    """AC-01: zero_crossing_rate is a float in [0.0, 1.0]."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["zero_crossing_rate"]
    assert isinstance(val, float), f"zero_crossing_rate must be float, got {type(val)}"
    assert val >= 0.0, f"zero_crossing_rate must be >= 0.0, got {val}"
    assert val <= 1.0, f"zero_crossing_rate must be <= 1.0, got {val}"


def test_mfcc_shape(sine_440: np.ndarray) -> None:
    """AC-01: mfcc is a list of exactly 13 floats."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["mfcc"]
    assert isinstance(val, list), f"mfcc must be list, got {type(val)}"
    assert len(val) == 13, f"mfcc must have 13 elements, got {len(val)}"
    assert all(isinstance(x, float) for x in val), (
        f"mfcc elements must all be float, got types: {[type(x) for x in val]}"
    )


def test_harmonic_ratio_range(sine_440: np.ndarray) -> None:
    """AC-01: harmonic_ratio is a float in [0.0, 1.0]."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["harmonic_ratio"]
    assert isinstance(val, float), f"harmonic_ratio must be float, got {type(val)}"
    assert val >= 0.0, f"harmonic_ratio must be >= 0.0, got {val}"
    assert val <= 1.0, f"harmonic_ratio must be <= 1.0, got {val}"


def test_tonnetz_shape(sine_440: np.ndarray) -> None:
    """AC-01: tonnetz is a list of exactly 6 floats."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)
    val = fv["tonnetz"]
    assert isinstance(val, list), f"tonnetz must be list, got {type(val)}"
    assert len(val) == 6, f"tonnetz must have 6 elements, got {len(val)}"
    assert all(isinstance(x, float) for x in val), (
        f"tonnetz elements must all be float, got types: {[type(x) for x in val]}"
    )


def test_silence_sentinel_values() -> None:
    """Edge case: silence (all zeros) returns sentinel values without raising.

    harmonic_ratio == 0.5 (guard branch for zero total energy),
    tonnetz == [0.0]*6 (NaN/Inf guard on silent HPSS output),
    spectral_flux == 0.0 (no frame-to-frame change on silence).
    """
    silence = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
    fv = extract_features(silence, sr=SAMPLE_RATE)

    assert fv["harmonic_ratio"] == 0.5, (
        f"harmonic_ratio sentinel for silence must be 0.5, got {fv['harmonic_ratio']}"
    )
    assert fv["tonnetz"] == [0.0] * 6, (
        f"tonnetz for silence must be [0.0]*6, got {fv['tonnetz']}"
    )
    assert fv["spectral_flux"] == 0.0, (
        f"spectral_flux for silence must be 0.0, got {fv['spectral_flux']}"
    )


def test_impulse_no_nan_inf() -> None:
    """Edge case: single-spike impulse produces finite values for all 7 new keys."""
    impulse = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
    impulse[22050] = 1.0

    fv = extract_features(impulse, sr=SAMPLE_RATE)

    scalar_keys = [
        "spectral_rolloff_hz",
        "spectral_flux",
        "zero_crossing_rate",
        "harmonic_ratio",
    ]
    for key in scalar_keys:
        assert np.isfinite(fv[key]), f"{key} is not finite for impulse input: {fv[key]}"

    vector_keys = ["spectral_contrast", "mfcc", "tonnetz"]
    for key in vector_keys:
        assert all(np.isfinite(x) for x in fv[key]), (
            f"{key} contains NaN/Inf for impulse input: {fv[key]}"
        )


def test_v1_keys_preserved(sine_440: np.ndarray) -> None:
    """AC-09: All 13 v1 keys remain present and correct in type/shape after Layer 1 widening."""
    fv = extract_features(sine_440, sr=SAMPLE_RATE)

    for key in V1_KEYS:
        assert key in fv, f"v1 key '{key}' missing from FeatureVector after Layer 1 widening"

    assert isinstance(fv["timestamp"], int), f"timestamp must be int, got {type(fv['timestamp'])}"
    assert isinstance(fv["chunk_index"], int), f"chunk_index must be int, got {type(fv['chunk_index'])}"
    assert isinstance(fv["source"], str), f"source must be str, got {type(fv['source'])}"
    assert isinstance(fv["duration_seconds"], float), (
        f"duration_seconds must be float, got {type(fv['duration_seconds'])}"
    )
    assert isinstance(fv["chroma"], list) and len(fv["chroma"]) == 12, (
        f"chroma must be list of 12, got len={len(fv['chroma'])}"
    )
    assert isinstance(fv["bpm"], float), f"bpm must be float, got {type(fv['bpm'])}"
    assert isinstance(fv["key_pitch_class"], int), (
        f"key_pitch_class must be int, got {type(fv['key_pitch_class'])}"
    )
    assert isinstance(fv["key_mode"], str), f"key_mode must be str, got {type(fv['key_mode'])}"
    assert isinstance(fv["rms_energy"], float), f"rms_energy must be float, got {type(fv['rms_energy'])}"
    assert isinstance(fv["spectral_centroid_hz"], float), (
        f"spectral_centroid_hz must be float, got {type(fv['spectral_centroid_hz'])}"
    )
    assert isinstance(fv["onset_strength"], float), (
        f"onset_strength must be float, got {type(fv['onset_strength'])}"
    )
    assert isinstance(fv["mel_spectrogram"], list) and isinstance(fv["mel_spectrogram"][0], list), (
        "mel_spectrogram must be list of lists"
    )
    assert isinstance(fv["waveform_display"], list), (
        f"waveform_display must be list, got {type(fv['waveform_display'])}"
    )
