"""Guard: audit each cited claim against its chunk.

Two layers:
1. Mechanical — cosine similarity between each claim and its cited chunk.
2. Judge — a fast model rates flagged claims 1-3 for actual entailment.

Claims rated 3 (unsupported) surface as flagged_gaps — topics worth raising
with the care team — instead of silent deletions.
"""

from __future__ import annotations

import json
import logging

import numpy as np

from patient_companion.agents.prompts import GROUNDING_JUDGE_SYSTEM, GROUNDING_TOOL_SCHEMA
from patient_companion.providers.base import EmbeddingProvider, LLMProvider
from patient_companion.schemas import Chunk, Citation

logger = logging.getLogger(__name__)

_MECH_THRESHOLD = 0.35


def _chunk_lookup(chunks: list[Chunk]) -> dict[tuple[str, int], Chunk]:
    return {(c.source, c.chunk_index): c for c in chunks}


def mechanical_scores(
    citations: list[Citation],
    chunks: list[Chunk],
    *,
    embedder: EmbeddingProvider,
) -> list[dict]:
    lookup = _chunk_lookup(chunks)
    pairs: list[tuple[str, Chunk]] = []
    for cit in citations:
        claim = cit.claim.strip()
        chunk = lookup.get((cit.source, cit.chunk_index))
        if claim and chunk and chunk.document:
            pairs.append((claim, chunk))
    if not pairs:
        return []

    # Chunks retrieved from the store carry their ingest-time vectors, so only
    # new claim text (and any chunk that lacks one) needs an embed call.
    texts: list[str] = []
    for claim, chunk in pairs:
        texts.append(claim)
        if chunk.embedding is None:
            texts.append(chunk.document)

    vecs = np.asarray(embedder.embed(texts), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    out = []
    vi = 0
    for claim, chunk in pairs:
        claim_vec = vecs[vi]
        vi += 1
        if chunk.embedding is not None:
            chunk_vec = np.asarray(chunk.embedding, dtype=np.float32)
            chunk_vec /= np.linalg.norm(chunk_vec) + 1e-12
        else:
            chunk_vec = vecs[vi]
            vi += 1
        cos = float(np.dot(claim_vec, chunk_vec))
        out.append(
            {
                "claim": claim,
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "cosine": cos,
                "flagged": cos < _MECH_THRESHOLD,
            }
        )
    return out


def judge_claims(
    mechanical: list[dict],
    chunks: list[Chunk],
    *,
    llm: LLMProvider,
    model: str,
) -> list[dict]:
    """Score all claims via the fast model; falls back to mechanical flags."""
    fallback = [{"claim": m["claim"], "score": 1 if not m["flagged"] else 3} for m in mechanical]
    if not mechanical:
        return fallback
    chunk_blob = "\n".join(
        f"[{c.source} idx={c.chunk_index}]\n{c.document[:1200]}" for c in chunks[:12]
    )
    payload = llm.complete_tool(
        system=GROUNDING_JUDGE_SYSTEM,
        user=(
            f"Chunks:\n{chunk_blob}\n\n"
            f"Mechanical check results:\n{json.dumps(mechanical[:20], ensure_ascii=False)}\n\n"
            "Return a score for each claim."
        ),
        tool_name="emit_grounding_scores",
        tool_description="Emit support scores for each claim.",
        input_schema=GROUNDING_TOOL_SCHEMA,
        model=model,
        max_tokens=800,
    )
    scores = payload.get("scores")
    return scores if isinstance(scores, list) and scores else fallback


def mechanical_gaps(mechanical: list[dict]) -> list[str]:
    """Gap strings for claims the cheap cosine check flagged."""
    return [
        f"Low overlap with cited source for: {m['claim'][:120]}…"
        for m in mechanical
        if m["flagged"]
    ]


def flagged_gaps(mechanical: list[dict], scores: list[dict]) -> list[str]:
    """Mechanical flags plus any claims the judge rated unsupported."""
    flagged = mechanical_gaps(mechanical)
    for s in scores:
        if s.get("score") == 3:
            claim = str(s.get("claim", ""))
            if claim and not any(claim[:40] in g for g in flagged):
                flagged.append(f"Could not verify in sources: {claim[:200]}")
    return flagged


def audit(
    rag_response: str,
    citations: list[Citation],
    chunks: list[Chunk],
    *,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    model: str,
) -> dict:
    """Return {verified_response, confidence, flagged_gaps, mechanical}."""
    mechanical = mechanical_scores(citations, chunks, embedder=embedder) if citations else []
    scores = judge_claims(mechanical, chunks, llm=llm, model=model)

    return {
        "verified_response": rag_response,
        "confidence": scores or [{"claim": rag_response[:120], "score": 1}],
        "flagged_gaps": flagged_gaps(mechanical, scores),
        "mechanical": mechanical,
    }
