"""Optional cross-encoder reranker.

Default backend is ``none`` — the LLM scope check plus dense-cosine gate
carry the load, keeping the app dependency-light. Set
``PC_RERANKER_BACKEND=fastembed`` and ``pip install '.[rerank]'`` for a
higher-precision ONNX reranker (no PyTorch).
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    def score(self, query: str, documents: list[str]) -> list[float] | None:
        """Relevance scores aligned with ``documents``; None to keep fused order."""
        ...


class NoneReranker:
    def score(self, query: str, documents: list[str]) -> list[float] | None:
        return None


class FastembedReranker:
    def __init__(self, model_name: str) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name=model_name)

    def score(self, query: str, documents: list[str]) -> list[float] | None:
        if not documents:
            return []
        try:
            return [float(s) for s in self._model.rerank(query, documents)]
        except Exception as e:  # pragma: no cover - depends on local model cache
            logger.warning("fastembed rerank failed, falling back to fused order: %s", e)
            return None


def get_reranker(backend: str, model_name: str) -> Reranker:
    if backend == "fastembed":
        try:
            return FastembedReranker(model_name)
        except Exception as e:  # pragma: no cover - env-dependent
            logger.warning("Could not init fastembed reranker (%s); using none.", e)
    return NoneReranker()
