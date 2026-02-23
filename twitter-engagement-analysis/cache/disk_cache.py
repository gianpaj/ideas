"""Lightweight JSON file cache with TTL support.

Cache files are stored in `.cache/` inside the project root (gitignored).
Keys are namespaced to avoid collisions between different data types.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / ".cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _key_path(namespace: str, identifier: str) -> Path:
    h = hashlib.md5(f"{namespace}:{identifier}".encode()).hexdigest()
    return _CACHE_DIR / f"{h}.json"


def get(namespace: str, identifier: str, ttl_hours: float = 24) -> object | None:
    """Return cached data, or None if absent / expired."""
    path = _key_path(namespace, identifier)
    if not path.exists():
        return None
    try:
        entry = json.loads(path.read_text())
        age_hours = (time.time() - entry["cached_at"]) / 3600
        if age_hours > ttl_hours:
            path.unlink(missing_ok=True)
            logger.debug("Cache expired for %s:%s", namespace, identifier)
            return None
        logger.debug("Cache hit for %s:%s (age %.1fh)", namespace, identifier, age_hours)
        return entry["data"]
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("Corrupt cache entry for %s:%s — %s", namespace, identifier, exc)
        path.unlink(missing_ok=True)
        return None


def set(namespace: str, identifier: str, data: object) -> None:  # noqa: A001
    """Write data to cache."""
    path = _key_path(namespace, identifier)
    try:
        path.write_text(json.dumps({"cached_at": time.time(), "data": data}))
        logger.debug("Cached %s:%s", namespace, identifier)
    except OSError as exc:
        logger.warning("Could not write cache for %s:%s — %s", namespace, identifier, exc)


def invalidate(namespace: str, identifier: str) -> None:
    """Remove a specific cache entry."""
    _key_path(namespace, identifier).unlink(missing_ok=True)


def clear_all() -> None:
    """Remove all cache files."""
    for f in _CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
    logger.info("Cache cleared.")
