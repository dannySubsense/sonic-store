"""Build a MusicGen text prompt from a FeatureVector dict (architecture doc section 2.6)."""

from typing import Any, Dict

_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _tempo_descriptor(bpm: float) -> str:
    """Map BPM to a tempo word."""
    if bpm < 70:
        return "slow"
    elif bpm < 100:
        return "moderate tempo"
    elif bpm < 130:
        return "upbeat"
    else:
        return "fast"


def _energy_descriptor(rms_energy: float) -> str:
    """Map normalized RMS energy to an energy phrase."""
    if rms_energy < 0.1:
        return "quiet, delicate"
    elif rms_energy < 0.4:
        return "moderate energy"
    else:
        return "energetic, driving"


def _timbre_descriptor(spectral_centroid_hz: float) -> str:
    """Map spectral centroid to a timbre phrase."""
    if spectral_centroid_hz < 1500:
        return "warm, bass-heavy"
    elif spectral_centroid_hz < 3500:
        return "balanced"
    else:
        return "bright, airy"


def build_prompt(features: Dict[str, Any]) -> str:
    """Convert a FeatureVector dict to a MusicGen text prompt string.

    Example output: 'upbeat balanced musical accompaniment, 124 BPM, D major,
    complementary to the input melody, instrumental'
    """
    bpm: float = float(features["bpm"])
    pitch_class: int = int(features["key_pitch_class"])
    mode: str = str(features["key_mode"])
    rms_energy: float = float(features["rms_energy"])
    spectral_centroid_hz: float = float(features["spectral_centroid_hz"])

    tempo_desc = _tempo_descriptor(bpm)
    energy_desc = _energy_descriptor(rms_energy)
    timbre_desc = _timbre_descriptor(spectral_centroid_hz)
    key_name = _KEY_NAMES[pitch_class % 12]

    prompt = (
        f"{energy_desc} {timbre_desc} musical accompaniment, "
        f"{tempo_desc}, {bpm:.0f} BPM, {key_name} {mode}, "
        f"complementary to the input melody, instrumental"
    )

    print(f"[PromptBuilder] {prompt}")
    return prompt
