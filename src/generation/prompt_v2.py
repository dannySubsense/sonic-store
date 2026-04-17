"""Prompt Builder v2 — trajectory-aware MusicGen prompt construction.

Accepts Layer 1 features + Layer 2 indicators. When indicators are available
(warm-up complete), incorporates trajectory descriptors per FR-03a..FR-03j.
When indicators are None or available=False, degrades to v1 build_prompt()
output exactly.

See specs/horizon-1/02-ARCHITECTURE.md §6 for full design.
"""

from typing import Any, Dict, Optional

from src.generation.prompt import build_prompt
from src.features.thresholds import (
    DELTA_BPM_THRESHOLD,
    KEY_STABLE_HIGH,
    KEY_STABLE_LOW,
    SPECTRAL_TREND_BRIGHTENING_THRESHOLD,
    SPECTRAL_TREND_DARKENING_THRESHOLD,
)

# --- Inline-duplicated helpers from src/generation/prompt.py ---
# Per 02-ARCHITECTURE.md §6.5: do NOT import the underscore-prefixed names
# from prompt.py. Inline-duplicate them here as local private helpers.

_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _tempo_descriptor(bpm: float) -> str:
    if bpm < 70:
        return "slow"
    elif bpm < 100:
        return "moderate tempo"
    elif bpm < 130:
        return "upbeat"
    else:
        return "fast"


def _energy_descriptor(rms_energy: float) -> str:
    if rms_energy < 0.1:
        return "quiet, delicate"
    elif rms_energy < 0.4:
        return "moderate energy"
    else:
        return "energetic, driving"


def _timbre_descriptor(spectral_centroid_hz: float) -> str:
    if spectral_centroid_hz < 1500:
        return "warm, bass-heavy"
    elif spectral_centroid_hz < 3500:
        return "balanced"
    else:
        return "bright, airy"


def build_prompt_v2(
    features: Dict[str, Any],
    indicators: Optional[Dict[str, Any]],
) -> str:
    """Build a MusicGen text prompt from Layer 1 features and Layer 2 indicators.

    When indicators is None or indicators["available"] is False,
    falls back to build_prompt(features) — identical to v1 output exactly.
    Otherwise constructs trajectory phrases per FR-03a..FR-03h and appends
    them to the v1 template.

    Output is always a non-empty natural-language string with no newlines,
    JSON, or special tokens.
    """
    # --- Cold-start fallback (FR-03i, AC-07) ---
    if indicators is None or not indicators.get("available", False):
        return build_prompt(features)

    # --- Trajectory phrase assembly (FR-03a..FR-03h, order: energy → tempo → key → timbre) ---
    trajectory_phrases = []

    # Energy regime (FR-03a, FR-03b)
    if indicators.get("energy_regime") == "rising":
        trajectory_phrases.append("building energy")
    elif indicators.get("energy_regime") == "falling":
        trajectory_phrases.append("fading energy")

    # Tempo delta (FR-03c, FR-03d)
    delta_bpm = indicators.get("delta_bpm")
    if delta_bpm is not None:
        if delta_bpm > DELTA_BPM_THRESHOLD:
            trajectory_phrases.append("accelerating")
        elif delta_bpm < -DELTA_BPM_THRESHOLD:
            trajectory_phrases.append("decelerating")

    # Key stability (FR-03e, FR-03f)
    key_stability = indicators.get("key_stability")
    if key_stability is not None:
        key_pc = int(features["key_pitch_class"]) % 12
        key_name = _KEY_NAMES[key_pc]
        mode = str(features["key_mode"])
        if key_stability > KEY_STABLE_HIGH:
            trajectory_phrases.append(f"harmonically stable in {key_name} {mode}")
        elif key_stability < KEY_STABLE_LOW:
            trajectory_phrases.append("shifting harmonically")

    # Spectral trend (FR-03g, FR-03h)
    spectral_trend = indicators.get("spectral_trend")
    if spectral_trend is not None:
        if spectral_trend > SPECTRAL_TREND_BRIGHTENING_THRESHOLD:
            trajectory_phrases.append("brightening timbre")
        elif spectral_trend < SPECTRAL_TREND_DARKENING_THRESHOLD:
            trajectory_phrases.append("darkening timbre")

    # --- Assemble output (§6.5) ---
    bpm = float(features["bpm"])
    pitch_class = int(features["key_pitch_class"]) % 12
    mode = str(features["key_mode"])
    rms_energy = float(features["rms_energy"])
    spectral_centroid_hz = float(features["spectral_centroid_hz"])

    tempo_desc = _tempo_descriptor(bpm)
    energy_desc = _energy_descriptor(rms_energy)
    timbre_desc = _timbre_descriptor(spectral_centroid_hz)
    key_name = _KEY_NAMES[pitch_class]

    if trajectory_phrases:
        trajectory = ", ".join(trajectory_phrases)
        prompt = (
            f"{energy_desc} {timbre_desc} musical accompaniment, "
            f"{tempo_desc}, {bpm:.0f} BPM, {key_name} {mode}, "
            f"{trajectory}, "
            f"complementary to the input melody, instrumental"
        )
    else:
        # No trajectory signals triggered — use v1 format exactly
        prompt = (
            f"{energy_desc} {timbre_desc} musical accompaniment, "
            f"{tempo_desc}, {bpm:.0f} BPM, {key_name} {mode}, "
            f"complementary to the input melody, instrumental"
        )

    return prompt
