"""
Lightweight in-memory result cache used to avoid repeating identical work.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Dict, Optional


def make_cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache:
    """Thread-safe LRU cache for small structured results."""

    def __init__(self, max_entries: int = 64):
        self._max_entries = max_entries
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._data:
                return None
            value = self._data.pop(key)
            self._data[key] = value
            return deepcopy(value)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            self._data[key] = deepcopy(value)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
