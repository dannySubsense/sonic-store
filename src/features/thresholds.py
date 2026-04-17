"""Named threshold constants for Horizon 1 trajectory descriptors.

All thresholds are importable constants, not environment variables.
They are initial calibration values; empirical tuning post-deployment
should result in updated values in this file (not scattered in code).
"""

# --- BPM delta thresholds ---
DELTA_BPM_THRESHOLD = 2.0

# --- Key stability thresholds ---
KEY_STABLE_HIGH = 0.75
KEY_STABLE_LOW = 0.40

# --- Energy momentum thresholds ---
ENERGY_MOMENTUM_RISING_THRESHOLD = 0.01
ENERGY_MOMENTUM_FALLING_THRESHOLD = -0.01

# --- Spectral trend thresholds (Hz per step) ---
SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50.0
SPECTRAL_TREND_DARKENING_THRESHOLD = -50.0

# --- Spectral flux normalization ---
# Calibrated from H1.S01 benchmark: p95 of raw flux across music-like fixtures
# (sine + chirp). Recalibrate during H1.S08 play-testing with real music if needed.
FLUX_NORM_DIVISOR = 203820.109375
