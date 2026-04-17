"""Unit tests for build_prompt_v2 — trajectory-aware prompt builder (H1.S04).

Covers: AC-06, AC-07, AC-08, AC-09.
13 test functions mapping 1:1 to the H1.S04 work items in specs/horizon-1/04-ROADMAP.md.
"""

import pytest
from src.generation.prompt_v2 import build_prompt_v2
from src.generation.prompt import build_prompt
from src.features.thresholds import (
    DELTA_BPM_THRESHOLD,
    KEY_STABLE_HIGH,
    KEY_STABLE_LOW,
    SPECTRAL_TREND_BRIGHTENING_THRESHOLD,
    SPECTRAL_TREND_DARKENING_THRESHOLD,
)


def make_features(bpm=120.0, key_pc=2, key_mode="major", rms=0.3, centroid=2000.0):
    """Minimal FeatureVector for prompt builder testing."""
    return {
        "bpm": float(bpm),
        "key_pitch_class": int(key_pc),
        "key_mode": key_mode,
        "rms_energy": float(rms),
        "spectral_centroid_hz": float(centroid),
    }


def make_indicators(
    available=True,
    delta_bpm=0.0,
    bpm_volatility=0.0,
    energy_momentum=0.0,
    energy_regime="stable",
    chroma_entropy=1.0,
    chroma_volatility=0.0,
    key_stability=0.5,
    spectral_trend=0.0,
    onset_regularity=0.0,
):
    """Build an indicator dict for prompt builder testing."""
    return {
        "available": available,
        "delta_bpm": delta_bpm,
        "bpm_volatility": bpm_volatility,
        "energy_momentum": energy_momentum,
        "energy_regime": energy_regime,
        "chroma_entropy": chroma_entropy,
        "chroma_volatility": chroma_volatility,
        "key_stability": key_stability,
        "spectral_trend": spectral_trend,
        "onset_regularity": onset_regularity,
    }


# --- AC-07: Cold-start fallback ---

def test_cold_start_none_indicators():
    """AC-07: build_prompt_v2(features, None) returns exact same string as build_prompt(features)."""
    features = make_features()
    assert build_prompt_v2(features, None) == build_prompt(features)


def test_cold_start_unavailable_indicators():
    """AC-07: build_prompt_v2 with available=False returns exact same string as build_prompt."""
    features = make_features()
    unavailable = {
        "available": False,
        "delta_bpm": None,
        "bpm_volatility": None,
        "energy_momentum": None,
        "energy_regime": None,
        "chroma_entropy": None,
        "chroma_volatility": None,
        "key_stability": None,
        "spectral_trend": None,
        "onset_regularity": None,
    }
    assert build_prompt_v2(features, unavailable) == build_prompt(features)


def test_no_exception_zero_history():
    """AC-07: build_prompt_v2 with None indicators (zero history) raises no exception."""
    build_prompt_v2(make_features(), None)


# --- AC-06: Trajectory descriptors present ---

def test_rising_energy_regime_descriptor():
    """AC-06: energy_regime='rising' produces a building/increasing/rising descriptor."""
    features = make_features()
    indicators = make_indicators(energy_regime="rising")
    out = build_prompt_v2(features, indicators)
    assert any(word in out.lower() for word in ["building", "increasing", "rising"])


def test_falling_energy_regime_descriptor():
    """AC-06: energy_regime='falling' produces a fading/diminishing/decreasing descriptor."""
    features = make_features()
    indicators = make_indicators(energy_regime="falling")
    out = build_prompt_v2(features, indicators)
    assert any(word in out.lower() for word in ["fading", "diminishing", "decreasing"])


def test_accelerating_bpm_descriptor():
    """AC-06: delta_bpm above DELTA_BPM_THRESHOLD produces an acceleration descriptor."""
    features = make_features()
    indicators = make_indicators(delta_bpm=DELTA_BPM_THRESHOLD + 3.0)
    out = build_prompt_v2(features, indicators)
    assert any(word in out.lower() for word in ["accelerating", "pushing tempo", "quickening"])


def test_decelerating_bpm_descriptor():
    """AC-06: delta_bpm below -DELTA_BPM_THRESHOLD produces a deceleration descriptor."""
    features = make_features()
    indicators = make_indicators(delta_bpm=-(DELTA_BPM_THRESHOLD + 3.0))
    out = build_prompt_v2(features, indicators)
    assert any(word in out.lower() for word in ["decelerating", "pulling back", "slowing"])


def test_key_stability_high_descriptor():
    """AC-06: key_stability above KEY_STABLE_HIGH produces 'harmonically stable' in output."""
    features = make_features(key_pc=0, key_mode="major")
    indicators = make_indicators(key_stability=KEY_STABLE_HIGH + 0.15)
    out = build_prompt_v2(features, indicators)
    assert "harmonically stable" in out


def test_spectral_trend_brightening_descriptor():
    """AC-06: spectral_trend above SPECTRAL_TREND_BRIGHTENING_THRESHOLD produces 'bright' in output."""
    features = make_features()
    indicators = make_indicators(spectral_trend=SPECTRAL_TREND_BRIGHTENING_THRESHOLD + 50.0)
    out = build_prompt_v2(features, indicators)
    assert "bright" in out.lower()


# --- AC-08: Output is valid MusicGen input ---

def test_output_is_nonempty_string():
    """AC-08: build_prompt_v2 with fully populated indicators returns a non-empty str."""
    features = make_features()
    indicators = make_indicators(
        energy_regime="rising",
        delta_bpm=5.0,
        key_stability=0.9,
        spectral_trend=100.0,
    )
    out = build_prompt_v2(features, indicators)
    assert isinstance(out, str)
    assert len(out) > 0


def test_output_no_newlines_or_json():
    """AC-08: Output contains no newlines, JSON braces, or array brackets."""
    features = make_features()
    indicators = make_indicators(
        energy_regime="rising",
        delta_bpm=5.0,
        key_stability=0.9,
        spectral_trend=100.0,
    )
    out = build_prompt_v2(features, indicators)
    assert "\n" not in out
    assert "{" not in out
    assert "[" not in out


# --- Regression snapshot ---

def test_snapshot_full_trajectory():
    """Regression guard: full trajectory prompt matches captured expected string.

    Fixture: bpm=130, key_pc=2 (D), key_mode='major', rms=0.5, centroid=3000.
    Indicators: rising energy, accelerating (delta_bpm=5.0), key_stability=0.9 (stable),
    spectral_trend=100.0 (brightening). Captured after initial implementation.
    """
    features = make_features(bpm=130.0, key_pc=2, key_mode="major", rms=0.5, centroid=3000.0)
    indicators = make_indicators(
        available=True,
        delta_bpm=5.0,
        energy_regime="rising",
        key_stability=0.9,
        spectral_trend=100.0,
    )
    expected = (
        "energetic, driving balanced musical accompaniment, "
        "fast, 130 BPM, D major, "
        "building energy, accelerating, harmonically stable in D major, brightening timbre, "
        "complementary to the input melody, instrumental"
    )
    actual = build_prompt_v2(features, indicators)
    assert actual == expected


# --- AC-09: v1 backward compatibility ---

def test_v1_prompt_callable_on_new_featurevector():
    """AC-09: build_prompt (v1) works on a 20-key FeatureVector (Layer 1 widened) without error."""
    feature_vector = {
        # Original 13 keys
        "timestamp": 0.0,
        "chunk_index": 0,
        "source": "test",
        "duration_seconds": 2.0,
        "chroma": [0.0] * 12,
        "bpm": 120.0,
        "key_pitch_class": 2,
        "key_mode": "major",
        "rms_energy": 0.3,
        "spectral_centroid_hz": 2000.0,
        "onset_strength": 0.5,
        "mel_spectrogram": [[0.0] * 10] * 128,
        "waveform_display": [0.0] * 2048,
        # 7 new Layer 1 keys
        "spectral_flux": 0.1,
        "mfcc": [0.0] * 13,
        "harmonic_ratio": 0.6,
        "tonnetz": [0.0] * 6,
        "spectral_rolloff_hz": 4000.0,
        "zero_crossing_rate": 0.05,
        "spectral_contrast": [0.0] * 7,
    }
    result = build_prompt(feature_vector)
    assert isinstance(result, str)
    assert len(result) > 0
