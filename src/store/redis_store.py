"""Redis-backed feature store with pipeline writes and TTL."""

import json
from typing import Any, Dict, List, Optional

import redis as redis_lib


FeatureVector = Dict[str, Any]

_LATEST_KEY = "features:latest"
_HISTORY_KEY = "features:history"
_LATEST_TTL = 60  # seconds
_HISTORY_MAX = 30


class RedisStore:
    """Redis implementation of the store interface; uses pipeline for atomic writes."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        url: Optional[str] = None,
    ) -> None:
        if url:
            self._client = redis_lib.Redis.from_url(url, decode_responses=True)
        else:
            self._client = redis_lib.Redis(
                host=host, port=port, db=db, decode_responses=True
            )

    def write(self, feature_vector: FeatureVector) -> None:
        """Persist feature_vector to Redis with pipeline; TTL=60s on latest key."""
        serialized = json.dumps(feature_vector)
        pipe = self._client.pipeline()
        pipe.setex(_LATEST_KEY, _LATEST_TTL, serialized)
        pipe.lpush(_HISTORY_KEY, serialized)
        pipe.ltrim(_HISTORY_KEY, 0, _HISTORY_MAX - 1)
        pipe.execute()

    def get_latest(self) -> Optional[FeatureVector]:
        """Return the most recent FeatureVector from Redis, or None if expired/absent."""
        raw = self._client.get(_LATEST_KEY)
        if raw is None:
            return None
        return json.loads(raw)

    def get_history(self, limit: int = _HISTORY_MAX) -> List[FeatureVector]:
        """Return up to limit entries from history list, newest first."""
        limit = min(limit, _HISTORY_MAX)
        entries = self._client.lrange(_HISTORY_KEY, 0, limit - 1)
        return [json.loads(e) for e in entries]

    def ping(self) -> bool:
        """Return True if Redis server is reachable."""
        try:
            return bool(self._client.ping())
        except Exception:
            return False
