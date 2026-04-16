"""Store package: select Redis or in-memory backend at startup."""

import os

from src.store.base import AbstractStore
from src.store.dict_store import DictStore


def get_store() -> AbstractStore:
    """Return RedisStore if available, otherwise DictStore fallback."""
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        from src.store.redis_store import RedisStore
        store = RedisStore(url=url)
        if store.ping():
            print(f"[store] Using Redis at {url}")
            return store
    except Exception as e:
        print(f"[store] Redis unavailable ({e}) — using in-memory store")
    store = DictStore()
    print("[store] Using in-memory DictStore")
    return store
