"""Unit tests for build_prompt with known feature vectors."""

import pytest

from src.generation.prompt import build_prompt


def make_feature_vector(
    bpm: float = 124.0,
    key_pitch_class: int = 2,   # D
    key_mode: str = "major",
    rms_energy: float = 0.25,
    spectral_centroid_hz: float = 2300.0,
) -> dict:
    return {
        "bpm": bpm,
        "key_pitch_class": key_pitch_class,
        "key_mode": key_mode,
        "rms_energy": rms_energy,
        "spectral_centroid_hz": spectral_centroid_hz,
    }


def test_build_prompt_returns_string() -> None:
    fv = make_feature_vector()
    result = build_prompt(fv)
    assert isinstance(result, str)
    assert len(result) > 0


def test_upbeat_tempo_descriptor() -> None:
    fv = make_feature_vector(bpm=124.0)
    result = build_prompt(fv)
    assert "upbeat" in result


def test_slow_tempo_descriptor() -> None:
    fv = make_feature_vector(bpm=60.0)
    result = build_prompt(fv)
    assert "slow" in result


def test_moderate_tempo_descriptor() -> None:
    fv = make_feature_vector(bpm=85.0)
    result = build_prompt(fv)
    assert "moderate tempo" in result


def test_fast_tempo_descriptor() -> None:
    fv = make_feature_vector(bpm=150.0)
    result = build_prompt(fv)
    assert "fast" in result


def test_key_name_d_major() -> None:
    fv = make_feature_vector(key_pitch_class=2, key_mode="major")
    result = build_prompt(fv)
    assert "D major" in result


def test_key_name_a_minor() -> None:
    fv = make_feature_vector(key_pitch_class=9, key_mode="minor")
    result = build_prompt(fv)
    assert "A minor" in result


def test_key_name_c_major() -> None:
    fv = make_feature_vector(key_pitch_class=0, key_mode="major")
    result = build_prompt(fv)
    assert "C major" in result


def test_quiet_energy_descriptor() -> None:
    fv = make_feature_vector(rms_energy=0.05)
    result = build_prompt(fv)
    assert "quiet" in result or "delicate" in result


def test_moderate_energy_descriptor() -> None:
    fv = make_feature_vector(rms_energy=0.25)
    result = build_prompt(fv)
    assert "moderate energy" in result


def test_energetic_driving_descriptor() -> None:
    fv = make_feature_vector(rms_energy=0.6)
    result = build_prompt(fv)
    assert "energetic" in result or "driving" in result


def test_warm_bass_heavy_timbre() -> None:
    fv = make_feature_vector(spectral_centroid_hz=1000.0)
    result = build_prompt(fv)
    assert "warm" in result or "bass-heavy" in result


def test_balanced_timbre() -> None:
    fv = make_feature_vector(spectral_centroid_hz=2300.0)
    result = build_prompt(fv)
    assert "balanced" in result


def test_bright_airy_timbre() -> None:
    fv = make_feature_vector(spectral_centroid_hz=4000.0)
    result = build_prompt(fv)
    assert "bright" in result or "airy" in result


def test_bpm_value_in_prompt() -> None:
    fv = make_feature_vector(bpm=124.0)
    result = build_prompt(fv)
    assert "124 BPM" in result


def test_instrumental_in_prompt() -> None:
    fv = make_feature_vector()
    result = build_prompt(fv)
    assert "instrumental" in result


def test_complementary_phrase_in_prompt() -> None:
    fv = make_feature_vector()
    result = build_prompt(fv)
    assert "complementary" in result
