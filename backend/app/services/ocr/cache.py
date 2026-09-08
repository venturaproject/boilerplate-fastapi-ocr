"""In-process TTL + LRU cache for synchronous OCR results, keyed by content hash.

Clients frequently retry the sync endpoint or send the same document twice; OCR is
expensive, so a short-lived cache pays off. Per-process only (not shared across
workers) — that's fine for the sync path.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict

from app.config import settings
from app.observability import metrics
from app.schemas.ocr import OcrResult

_lock = threading.Lock()
_store: OrderedDict[str, tuple[float, OcrResult]] = OrderedDict()


def key_for(data: bytes, lang: str, max_pages: int | None) -> str:
    h = hashlib.sha256()
    h.update(data)
    h.update(f"|{lang}|{max_pages}".encode())
    return h.hexdigest()


def get(key: str) -> OcrResult | None:
    ttl = settings.ocr_sync_cache_ttl_seconds
    if ttl <= 0:
        return None
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry is None:
            metrics.record_cache("miss")
            return None
        ts, result = entry
        if now - ts > ttl:
            _store.pop(key, None)
            metrics.record_cache("miss")
            return None
        _store.move_to_end(key)
    metrics.record_cache("hit")
    return result


def put(key: str, result: OcrResult) -> None:
    if settings.ocr_sync_cache_ttl_seconds <= 0:
        return
    with _lock:
        _store[key] = (time.monotonic(), result)
        _store.move_to_end(key)
        while len(_store) > max(1, settings.ocr_sync_cache_max_entries):
            _store.popitem(last=False)


def clear() -> None:
    with _lock:
        _store.clear()
