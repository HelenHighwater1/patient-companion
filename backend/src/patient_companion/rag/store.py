"""Per-disease knowledge store.

Layout on disk (gitignored, built by ``rag.ingest``)::

    knowledge/<disease>/store/
        rows.json        chunk records with provenance
        embeddings.npy   float32 matrix, row-aligned with rows.json
        bm25.pkl         pickled tokenized corpus (rebuilt in memory)
        manifest.json    what was ingested, when, with which model

The corpus is small (hundreds of chunks), so dense search is a brute-force
cosine against a numpy matrix — no vector DB required.
"""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class KnowledgeStore:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.rows: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None
        self._bm25: BM25Okapi | None = None

    # -- persistence ---------------------------------------------------------

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "rows.json").write_text(
            json.dumps(self.rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        if self.embeddings is not None:
            np.save(self.dir / "embeddings.npy", self.embeddings.astype(np.float32))
        with open(self.dir / "bm25.pkl", "wb") as f:
            pickle.dump([tokenize(r["document"]) for r in self.rows], f)

    def load(self) -> bool:
        rows_path = self.dir / "rows.json"
        emb_path = self.dir / "embeddings.npy"
        bm25_path = self.dir / "bm25.pkl"
        if not rows_path.exists():
            return False
        self.rows = json.loads(rows_path.read_text(encoding="utf-8"))
        if emb_path.exists():
            self.embeddings = np.load(emb_path)
        if bm25_path.exists():
            with open(bm25_path, "rb") as f:
                tokenized = pickle.load(f)
            if tokenized:
                self._bm25 = BM25Okapi(tokenized)
        return bool(self.rows)

    @property
    def size(self) -> int:
        return len(self.rows)

    # -- search ----------------------------------------------------------------

    def dense_search(self, query_embedding: list[float], k: int) -> list[tuple[int, float]]:
        """Return [(row_index, cosine_similarity)] sorted best-first."""
        if self.embeddings is None or not self.rows:
            return []
        q = np.asarray(query_embedding, dtype=np.float32)
        emb = self.embeddings
        qn = q / (np.linalg.norm(q) + 1e-12)
        en = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12)
        sims = en @ qn
        top = np.argsort(sims)[::-1][:k]
        return [(int(i), float(sims[i])) for i in top]

    def bm25_search(self, query: str, k: int) -> list[int]:
        """Return row indices best-first (BM25 scores are not comparable across corpora)."""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        top = np.argsort(scores)[::-1][:k]
        return [int(i) for i in top if scores[i] > 0]
