"""Rolling min-max normalizer for RMS energy and onset strength."""

from collections import deque
from typing import Deque


class RollingNormalizer:
    """Track rolling min/max over a fixed window; normalize new values to [0, 1]."""

    def __init__(self, window_size: int = 60) -> None:
        self._window: Deque[float] = deque(maxlen=window_size)

    def normalize(self, value: float) -> float:
        """Add value to window and return normalized result."""
        self._window.append(value)
        lo = min(self._window)
        hi = max(self._window)
        if hi == lo:
            return 0.0
        return float((value - lo) / (hi - lo))
