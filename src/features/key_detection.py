"""Krumhansl-Schmuckler key detection from a 12-element chroma vector."""

from typing import Tuple

import numpy as np

# Krumhansl-Schmuckler key profiles (Krumhansl 1990)
# Index 0 = C, 1 = C#, ..., 11 = B
_MAJOR_PROFILE = np.array([
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
], dtype=np.float32)

_MINOR_PROFILE = np.array([
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
], dtype=np.float32)

_KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key(chroma: np.ndarray) -> Tuple[int, str]:
    """Correlate chroma vector against K-S profiles; return (pitch_class, mode).

    pitch_class is 0-11 (0=C). mode is 'major' or 'minor'.
    """
    chroma = np.asarray(chroma, dtype=np.float32)
    if chroma.shape != (12,):
        raise ValueError(f"chroma must have shape (12,), got {chroma.shape}")

    best_r = -np.inf
    best_pitch = 0
    best_mode = "major"

    for pitch in range(12):
        rotated = np.roll(chroma, -pitch)

        r_major = float(np.corrcoef(rotated, _MAJOR_PROFILE)[0, 1])
        r_minor = float(np.corrcoef(rotated, _MINOR_PROFILE)[0, 1])

        if r_major > best_r:
            best_r = r_major
            best_pitch = pitch
            best_mode = "major"

        if r_minor > best_r:
            best_r = r_minor
            best_pitch = pitch
            best_mode = "minor"

    return best_pitch, best_mode


def key_name(pitch_class: int) -> str:
    """Return the note name string for a pitch class integer 0-11."""
    return _KEY_NAMES[pitch_class % 12]
