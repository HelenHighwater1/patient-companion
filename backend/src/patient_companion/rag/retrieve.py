"""Hybrid retrieval: scope-check + rewrite → dense+BM25 → RRF → optional rerank → gate.

Every stage reports latency so the API can expose retrieval diagnostics.
The gate has two layers: the LLM scope check runs *before* any retrieval
spend, and the score gate (rerank margin or dense cosine floor) is the
safety net for low-confidence matches.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from patient_companion.config import Settings, get_settings
from patient_companion.providers.base import EmbeddingProvider, LLMProvider
from patient_companion.rag.rerank import Reranker, get_reranker
from patient_companion.rag.rewrite import plan_retrieval
from patient_companion.rag.store import KnowledgeStore
from patient_companion.schemas import Chunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunks: list[Chunk] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    query_variants: list[str] = field(default_factory=list)
    top_dense_cosine: float | None = None
    latencies_ms: dict[str, float] = field(default_factory=dict)


def _rrf_fuse(rank_lists: list[list[int]], k: int) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + r + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


class Retriever:
    def __init__(
        self,
        store: KnowledgeStore,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        *,
        settings: Settings | None = None,
        reranker: Reranker | None = None,
        disease_label: str = "ALS (amyotrophic lateral sclerosis)",
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store
        self.embedder = embedder
        self.llm = llm
        self.disease_label = disease_label
        self.reranker = reranker or get_reranker(
            self.settings.reranker_backend, self.settings.reranker_model
        )

    def retrieve(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        *,
        top_k: int | None = None,
        skip_rewrite: bool = False,
    ) -> RetrievalResult:
        s = self.settings
        k = top_k or s.top_k
        result = RetrievalResult()
        t0 = time.perf_counter()

        if skip_rewrite:
            plan: dict[str, Any] = {"queries": [question.strip()], "in_scope": True}
        else:
            plan = plan_retrieval(
                question,
                conversation_history,
                llm=self.llm,
                model=s.llm_model_fast,
                disease_label=self.disease_label,
            )
        result.latencies_ms["rewrite_ms"] = _ms(t0)
        result.query_variants = plan["queries"]

        if not plan.get("in_scope", True):
            result.refused = True
            result.refusal_reason = "out_of_scope"
            result.latencies_ms["total_ms"] = _ms(t0)
            return result
        if not result.query_variants:
            result.refused = True
            result.refusal_reason = "empty_query"
            result.latencies_ms["total_ms"] = _ms(t0)
            return result
        if not self.store.size:
            raise RuntimeError(
                f"Knowledge store is empty for '{s.default_disease}'. "
                "Run: python -m patient_companion.rag.ingest"
            )

        t = time.perf_counter()
        q_embeddings = self.embedder.embed(result.query_variants)
        result.latencies_ms["embed_ms"] = _ms(t)

        dense_rank_lists: list[list[int]] = []
        dense_cosines: dict[int, float] = {}
        t = time.perf_counter()
        for qe in q_embeddings:
            hits = self.store.dense_search(qe, min(s.dense_candidates, self.store.size))
            dense_rank_lists.append([i for i, _ in hits])
            for i, cos in hits:
                if cos > dense_cosines.get(i, -1.0):
                    dense_cosines[i] = cos
        result.latencies_ms["dense_ms"] = _ms(t)

        bm25_rank_lists: list[list[int]] = []
        t = time.perf_counter()
        for var in result.query_variants:
            bm25_rank_lists.append(self.store.bm25_search(var, min(s.bm25_candidates, self.store.size)))
        result.latencies_ms["bm25_ms"] = _ms(t)

        fused = _rrf_fuse(dense_rank_lists + bm25_rank_lists, s.rrf_k)
        candidate_indices = [idx for idx, _ in fused[: s.fusion_pool_size]]
        if not candidate_indices:
            result.refused = True
            result.refusal_reason = "no_candidates"
            result.latencies_ms["total_ms"] = _ms(t0)
            return result

        docs = [self.store.rows[i]["document"] for i in candidate_indices]
        t = time.perf_counter()
        rerank_scores = self.reranker.score(result.query_variants[0], docs)
        result.latencies_ms["rerank_ms"] = _ms(t)

        if rerank_scores is not None:
            order = list(np.argsort(np.asarray(rerank_scores))[::-1])
            sorted_desc = sorted(rerank_scores, reverse=True)
            top1 = sorted_desc[0]
            tail = sorted_desc[min(10, len(sorted_desc)) - 1]
            if (top1 - tail) < s.gate_min_rerank_margin and top1 < 0.0:
                result.refused = True
                result.refusal_reason = "low_source_confidence"
        else:
            order = list(range(len(candidate_indices)))
            best_cos = max(dense_cosines.get(i, 0.0) for i in candidate_indices)
            result.top_dense_cosine = best_cos
            if best_cos < s.gate_min_dense_cosine:
                result.refused = True
                result.refusal_reason = "low_source_confidence"

        if result.refused:
            result.latencies_ms["total_ms"] = _ms(t0)
            return result

        n = max(1, len(order))
        for rank, li in enumerate(order[:k]):
            row = self.store.rows[candidate_indices[li]]
            chunk = Chunk(
                document=row["document"],
                source=row.get("source", "?"),
                chunk_index=row.get("chunk_index", 0),
                relevance=round(1.0 - rank / n, 4),
                title=row.get("title"),
                section=row.get("section"),
                section_path=row.get("section_path"),
                source_id=row.get("source_id"),
                url=row.get("url"),
                year=row.get("year"),
                rerank_score=(float(rerank_scores[li]) if rerank_scores is not None else None),
            )
            result.chunks.append(chunk)

        result.latencies_ms["total_ms"] = _ms(t0)
        return result


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def refusal_message() -> str:
    return (
        "I don't have reliable sources in this demo knowledge base to answer that "
        "safely. Please ask your care team — or try a question about ALS symptoms, "
        "progression, breathing, nutrition, or planning your care. This tool is for "
        "education only and is not medical advice."
    )
