"""AbstractStore protocol defining the read/write interface for feature state."""

from typing import Any, Dict, List, Optional, Protocol


FeatureVector = Dict[str, Any]


class AbstractStore(Protocol):
    """Protocol that both RedisStore and DictStore must satisfy."""

    def write(self, feature_vector: FeatureVector) -> None:
        """Persist feature_vector as latest and prepend to history."""
        ...

    def get_latest(self) -> Optional[FeatureVector]:
        """Return the most recently written FeatureVector, or None."""
        ...

    def get_history(self, limit: int = 30) -> List[FeatureVector]:
        """Return up to limit entries from history, newest first."""
        ...

    def ping(self) -> bool:
        """Return True if the store backend is reachable."""
        ...
