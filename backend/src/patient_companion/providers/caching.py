"""Content-hash embedding cache.

Embeddings are a pure function of (model, text), so caching is exact — never
stale. This matters because the grounding audit re-embeds the same source
chunks on every question, and the retrieval planner tends to emit identical
query variants across a conversation. After warmup, those repeat API calls
disappear entirely.
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict

from patient_companion.providers.base import EmbeddingProvider


class CachingEmbedder:
    """LRU cache over an EmbeddingProvider, keyed by SHA-256 of the text."""

    def __init__(self, inner: EmbeddingProvider, max_entries: int = 4096) -> None:
        self._inner = inner
        self._max_entries = max_entries
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()

    def __getattr__(self, name: str):
        # Pass through provider attributes (e.g. ``_model`` for the manifest).
        return getattr(self._inner, name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        key_of = {t: hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts}
        out: dict[str, list[float]] = {}
        with self._lock:
            missing = set()
            for t in texts:
                k = key_of[t]
                if k in self._cache:
                    self._cache.move_to_end(k)
                    out[k] = self._cache[k]
                else:
                    missing.add(t)
        if missing:
            ordered = sorted(missing)
            fresh = self._inner.embed(ordered)
            with self._lock:
                for t, vec in zip(ordered, fresh, strict=True):
                    k = key_of[t]
                    self._cache[k] = vec
                    out[k] = vec
                while len(self._cache) > self._max_entries:
                    self._cache.popitem(last=False)
        return [out[key_of[t]] for t in texts]
