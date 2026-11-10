"""Guard: audit each cited claim against its chunk.

Two layers:
1. Mechanical — cosine similarity between each claim and its cited chunk.
2. Judge — a fast model rates flagged claims 1-3 for actual entailment.

Claims rated 3 (unsupported) surface as flagged_gaps, which the tone agent
turns into "worth asking your doctor" topics instead of silent deletions.
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


def _chunk_lookup(chunks: list[Chunk]) -> dict[tuple[str, int], str]:
    return {(c.source, c.chunk_index): c.document for c in chunks}


def mechanical_scores(
    citations: list[Citation],
    chunks: list[Chunk],
    *,
    embedder: EmbeddingProvider,
) -> list[dict]:
    lookup = _chunk_lookup(chunks)
    texts: list[str] = []
    meta: list[tuple[str, str, int]] = []
    for cit in citations:
        claim = cit.claim.strip()
        chunk_txt = lookup.get((cit.source, cit.chunk_index), "")
        if claim and chunk_txt:
            texts += [claim, chunk_txt]
            meta.append((claim, cit.source, cit.chunk_index))
    if not meta:
        return []

    vecs = np.asarray(embedder.embed(texts), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    out = []
    for i, (claim, src, idx) in enumerate(meta):
        cos = float(np.dot(vecs[i * 2], vecs[i * 2 + 1]))
        out.append(
            {
                "claim": claim,
                "source": src,
                "chunk_index": idx,
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

    flagged: list[str] = [
        f"Low overlap with cited source for: {m['claim'][:120]}…"
        for m in mechanical
        if m["flagged"]
    ]
    for s in scores:
        if s.get("score") == 3:
            claim = str(s.get("claim", ""))
            if claim and not any(claim[:40] in g for g in flagged):
                flagged.append(f"Could not verify in sources: {claim[:200]}")

    return {
        "verified_response": rag_response,
        "confidence": scores or [{"claim": rag_response[:120], "score": 1}],
        "flagged_gaps": flagged,
        "mechanical": mechanical,
    }
