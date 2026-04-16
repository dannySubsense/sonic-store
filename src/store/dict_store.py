"""In-memory feature store using a Python dict and deque. No external dependencies."""

import json
import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional


FeatureVector = Dict[str, Any]

_HISTORY_MAX = 30


class DictStore:
    """In-memory fallback store with identical interface to RedisStore."""

    def __init__(self, history_max: int = _HISTORY_MAX) -> None:
        self._latest: Optional[str] = None  # JSON string
        self._history: Deque[str] = deque(maxlen=history_max)
        self._history_max = history_max
        self._lock = threading.Lock()

    def write(self, feature_vector: FeatureVector) -> None:
        """Store feature_vector as latest and prepend to history."""
        serialized = json.dumps(feature_vector)
        with self._lock:
            self._latest = serialized
            self._history.appendleft(serialized)

    def get_latest(self) -> Optional[FeatureVector]:
        """Return most recently written FeatureVector, or None if empty."""
        with self._lock:
            if self._latest is None:
                return None
            return json.loads(self._latest)

    def get_history(self, limit: int = _HISTORY_MAX) -> List[FeatureVector]:
        """Return up to limit entries from history, newest first."""
        limit = min(limit, self._history_max)
        with self._lock:
            entries = list(self._history)[:limit]
        return [json.loads(e) for e in entries]

    def ping(self) -> bool:
        """Always reachable — in-memory store needs no external connection."""
        return True
