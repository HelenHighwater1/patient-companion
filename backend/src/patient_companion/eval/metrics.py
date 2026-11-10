"""Eval metrics: recall@k, MRR, refusal accuracy."""

from __future__ import annotations

from patient_companion.schemas import Chunk


def _source_match(chunk: Chunk, needle: str) -> bool:
    hay = f"{chunk.source} {chunk.source_id or ''} {chunk.title or ''}".lower()
    return needle.lower() in hay


def recall_at_k(chunks: list[Chunk], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    top = chunks[:k]
    hits = sum(1 for e in expected if any(_source_match(c, e) for c in top))
    return hits / len(expected)


def reciprocal_rank(chunks: list[Chunk], expected: list[str]) -> float:
    for i, c in enumerate(chunks):
        if any(_source_match(c, e) for e in expected):
            return 1.0 / (i + 1)
    return 0.0
