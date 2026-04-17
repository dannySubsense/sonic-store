"""Feature extraction engine: audio chunk -> FeatureVector dict.

Layer 1 widening (Horizon 1): extract_features() now returns 20 keys.
The original 13 v1 keys are preserved unchanged in name, type, and shape.
Seven new keys are appended: spectral_rolloff_hz, spectral_flux,
spectral_contrast, zero_crossing_rate, mfcc, harmonic_ratio, tonnetz.
"""

import time
from typing import Any, Dict, List

import librosa
import numpy as np

from src.features.key_detection import detect_key
from src.features.thresholds import FLUX_NORM_DIVISOR

# Type alias matching the FeatureVector JSON schema (section 3.1 of architecture doc)
FeatureVector = Dict[str, Any]

_chunk_counter: int = 0


def extract_features(
    audio: np.ndarray,
    sr: int = 22050,
    source: str = "mic",
    chunk_index: int | None = None,
) -> FeatureVector:
    """Extract all 20 features from a float32 audio chunk; return FeatureVector dict.

    audio: float32 ndarray of shape (44100,), values in [-1, 1].

    Returns 13 original v1 keys plus 7 Layer 1 widening keys (Horizon 1):
    spectral_rolloff_hz, spectral_flux, spectral_contrast, zero_crossing_rate,
    mfcc, harmonic_ratio, tonnetz.
    """
    global _chunk_counter

    audio = np.asarray(audio, dtype=np.float32)

    if chunk_index is None:
        chunk_index = _chunk_counter
    _chunk_counter += 1

    timestamp = int(time.time() * 1000)
    duration_seconds = len(audio) / sr

    # --- chroma (CQT-based) ---
    chroma_matrix = librosa.feature.chroma_cqt(y=audio, sr=sr)
    chroma: List[float] = chroma_matrix.mean(axis=1).tolist()

    # --- BPM ---
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    # librosa 0.10.x may return ndarray; safely extract scalar
    bpm = float(np.atleast_1d(tempo)[0])

    # --- key (Krumhansl-Schmuckler) ---
    chroma_arr = np.array(chroma, dtype=np.float32)
    key_pitch_class, key_mode = detect_key(chroma_arr)

    # --- RMS energy (normalized 0-1) ---
    rms_matrix = librosa.feature.rms(y=audio)
    raw_rms = float(rms_matrix.mean())
    # Typical speech/music RMS tops out around 0.3; clamp to [0, 1]
    rms_energy = float(np.clip(raw_rms / 0.3, 0.0, 1.0))

    # --- spectral centroid (Hz) ---
    cent_matrix = librosa.feature.spectral_centroid(y=audio, sr=sr)
    spectral_centroid_hz = float(cent_matrix.mean())

    # --- onset strength (normalized 0-1) ---
    onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
    raw_onset = float(onset_env.mean())
    # onset_strength is unbounded; practical max ~10; clamp to [0, 1]
    onset_strength = float(np.clip(raw_onset / 10.0, 0.0, 1.0))

    # --- mel spectrogram (128 x T), power -> dB, normalized per frame ---
    mel_power = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128)
    mel_db = librosa.power_to_db(mel_power, ref=np.max)
    # Normalize each frame to [0, 1] for display
    frame_min = mel_db.min(axis=0, keepdims=True)
    frame_max = mel_db.max(axis=0, keepdims=True)
    denom = np.where(frame_max - frame_min == 0, 1.0, frame_max - frame_min)
    mel_norm = (mel_db - frame_min) / denom
    mel_spectrogram: List[List[float]] = mel_norm.tolist()

    # --- waveform display (downsampled to 2048 points) ---
    n_display = 2048
    if len(audio) >= n_display:
        indices = np.linspace(0, len(audio) - 1, n_display, dtype=int)
        waveform_display: List[float] = audio[indices].tolist()
    else:
        waveform_display = audio.tolist()

    # --- Layer 1 widening (Horizon 1) — 7 new keys ---

    # --- spectral rolloff (Hz) ---
    rolloff_matrix = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)
    spectral_rolloff_hz = float(rolloff_matrix.mean())

    # --- spectral flux (normalized [0, 1]) ---
    S = np.abs(librosa.stft(audio))                        # shape (1 + n_fft/2, T)
    flux_frames = np.sum(np.diff(S, axis=1) ** 2, axis=0)  # shape (T-1,)
    raw_flux = float(flux_frames.mean()) if flux_frames.size > 0 else 0.0
    spectral_flux = float(np.clip(raw_flux / FLUX_NORM_DIVISOR, 0.0, 1.0))

    # --- spectral contrast (length 7, dB log-ratio per subband) ---
    contrast_matrix = librosa.feature.spectral_contrast(y=audio, sr=sr, n_bands=6)
    spectral_contrast: List[float] = contrast_matrix.mean(axis=1).tolist()  # length 7

    # --- zero crossing rate (normalized [0, 1]) ---
    zcr_matrix = librosa.feature.zero_crossing_rate(y=audio)
    raw_zcr = float(zcr_matrix.mean())
    zero_crossing_rate = float(np.clip(raw_zcr / 0.3, 0.0, 1.0))

    # --- MFCC (length 13, mean over time frames) ---
    mfcc_matrix = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
    mfcc: List[float] = mfcc_matrix.mean(axis=1).tolist()  # length 13

    # --- HPSS (shared decomposition for harmonic_ratio and tonnetz) ---
    harmonic, percussive = librosa.effects.hpss(audio)
    h_energy = float(np.sum(harmonic ** 2))
    p_energy = float(np.sum(percussive ** 2))
    total_energy = h_energy + p_energy

    # --- harmonic ratio ([0, 1]; 0.5 sentinel for silence) ---
    if total_energy < 1e-8:
        harmonic_ratio = 0.5
    else:
        harmonic_ratio = float(np.clip(h_energy / total_energy, 0.0, 1.0))

    # --- tonnetz (length 6; uses harmonic component for stable tonal centroid) ---
    harmonic_for_tonnetz = harmonic if total_energy >= 1e-8 else audio
    tonnetz_matrix = librosa.feature.tonnetz(y=harmonic_for_tonnetz, sr=sr)
    tonnetz: List[float] = tonnetz_matrix.mean(axis=1).tolist()  # length 6
    if any(np.isnan(t) or np.isinf(t) for t in tonnetz):
        tonnetz = [0.0] * 6

    return {
        # --- v1 keys (13) — unchanged ---
        "timestamp": timestamp,
        "chunk_index": chunk_index,
        "source": source,
        "duration_seconds": duration_seconds,
        "chroma": chroma,
        "bpm": bpm,
        "key_pitch_class": key_pitch_class,
        "key_mode": key_mode,
        "rms_energy": rms_energy,
        "spectral_centroid_hz": spectral_centroid_hz,
        "onset_strength": onset_strength,
        "mel_spectrogram": mel_spectrogram,
        "waveform_display": waveform_display,
        # --- Layer 1 widening keys (7) ---
        "spectral_rolloff_hz": spectral_rolloff_hz,
        "spectral_flux": spectral_flux,
        "spectral_contrast": spectral_contrast,
        "zero_crossing_rate": zero_crossing_rate,
        "mfcc": mfcc,
        "harmonic_ratio": harmonic_ratio,
        "tonnetz": tonnetz,
    }
