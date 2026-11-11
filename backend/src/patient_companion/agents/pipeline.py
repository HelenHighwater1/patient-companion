"""Pipeline orchestration.

Each entry point yields plain-dict events — the server layer serializes
them to SSE. Nothing here knows about HTTP.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Any

from patient_companion.agents.answer import answer_question
from patient_companion.agents.distress import is_distressed
from patient_companion.agents.guard import audit
from patient_companion.agents.intake import iter_document_sections
from patient_companion.agents.prep import generate_prep_sheet
from patient_companion.agents.tone import apply_tone
from patient_companion.config import Settings, get_settings
from patient_companion.providers.base import EmbeddingProvider, LLMProvider
from patient_companion.rag.retrieve import Retriever, refusal_message
from patient_companion.schemas import (
    CARD_LABELS,
    DEMO_DISCLAIMER,
    Chunk,
    PrepSheet,
    ReadingLevel,
)

logger = logging.getLogger(__name__)

EXCERPT_CHARS = 900


# Chunks are embedded with a leading "[Section > Subsection]" breadcrumb.
_BREADCRUMB = re.compile(r"^\[[^\]]*\]\s*")


def _excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    text = _BREADCRUMB.sub("", " ".join(text.split()))
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def source_view(c: Chunk) -> dict[str, Any]:
    """A retrieved chunk as the UI's evidence panel shows it."""
    return {
        "source": c.source,
        "chunk_index": c.chunk_index,
        "title": c.title,
        "url": c.url,
        "section": c.section,
        "section_path": c.section_path,
        "year": c.year,
        "source_type": c.source_type,
        "excerpt": _excerpt(c.document),
        "relevance": c.relevance,
        "dense_cosine": c.dense_cosine,
        "fusion_score": c.fusion_score,
        "rerank_score": c.rerank_score,
    }


def stream_document_summary(
    document_text: str,
    *,
    llm: LLMProvider,
    settings: Settings | None = None,
) -> Iterator[dict[str, Any]]:
    """Document → staged card events → done (with document_context for chat).

    Each card is emitted as soon as its own LLM call completes, so the
    patient can start reading while later sections are still generating.
    """
    s = settings or get_settings()
    yield {"type": "status", "stage": "reading"}
    label_for = dict(CARD_LABELS)
    parts: dict[str, Any] = {}
    generated: set[str] = set()
    index = 0
    for key, value, from_model in iter_document_sections(document_text, llm=llm, model=s.llm_model_strong):
        parts[key] = value
        if from_model:
            generated.add(key)
        if key == "patient_concerns":
            if value:
                yield {"type": "concerns", "items": value}
        else:
            yield {
                "type": "card",
                "index": index,
                "key": key,
                "label": label_for[key],
                "body": value,
            }
            index += 1
    context = "\n".join(
        part
        for key in ("orientation", "main_finding", "evidence", "next_steps")
        if key in generated and isinstance(part := parts.get(key), str) and part
    )
    yield {
        "type": "done",
        "document_context": context,
        "patient_concerns": parts.get("patient_concerns") or [],
    }


def stream_answer(
    question: str,
    conversation_history: list[dict] | None,
    document_context: str | None,
    reading_level: ReadingLevel,
    *,
    retriever: Retriever,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    settings: Settings | None = None,
) -> Iterator[dict[str, Any]]:
    """Question → retrieve → answer → guard → tone, with progress events."""
    s = settings or get_settings()
    q = (question or "").strip()
    if not q:
        yield {"type": "refusal", "message": "Please enter a question."}
        yield {"type": "done"}
        return

    yield {"type": "status", "stage": "searching"}
    result = retriever.retrieve(q, conversation_history)
    yield {
        "type": "retrieval",
        **result.trace(),
        "sources": [source_view(c) for c in result.chunks],
    }
    if result.refused:
        yield {
            "type": "refusal",
            "message": refusal_message(),
            "reason": result.refusal_reason,
        }
        yield {"type": "done"}
        return

    yield {"type": "status", "stage": "answering"}
    ans = answer_question(
        q,
        result.chunks,
        llm=llm,
        model=s.llm_model_strong,
        document_context=document_context,
    )

    yield {"type": "status", "stage": "checking"}
    checked = audit(
        ans["response"],
        ans["citations"],
        result.chunks,
        embedder=embedder,
        llm=llm,
        model=s.llm_model_fast,
    )

    yield {"type": "status", "stage": "rewriting"}
    toned = apply_tone(
        checked["verified_response"],
        checked["flagged_gaps"],
        llm=llm,
        model=s.llm_model_strong,
        reading_level=reading_level,
        distress=is_distressed(q),
    )

    chunk_meta = {(c.source, c.chunk_index): c for c in result.chunks}
    mechanical = {(m["source"], m["chunk_index"], m["claim"]): m for m in checked["mechanical"]}
    judge = {str(sc.get("claim", "")).strip(): sc.get("score") for sc in checked["confidence"]}
    markers_by_chunk: dict[tuple[str, int], list[int]] = {}
    for c in ans["citations"]:
        markers_by_chunk.setdefault((c.source, c.chunk_index), []).append(c.marker)

    def _citation_view(c) -> dict:
        meta = chunk_meta.get((c.source, c.chunk_index)) or Chunk(document="", source=c.source)
        mech = mechanical.get((c.source, c.chunk_index, c.claim.strip()))
        return {
            "marker": c.marker,
            "claim": c.claim,
            "source": c.source,
            "chunk_index": c.chunk_index,
            "title": meta.title,
            "url": meta.url,
            "grounding": {
                "cosine": round(mech["cosine"], 4) if mech else None,
                "flagged": bool(mech["flagged"]) if mech else False,
                "judge_score": judge.get(c.claim.strip()),
            },
        }

    def _answer_source_view(c: Chunk) -> dict:
        markers = markers_by_chunk.get((c.source, c.chunk_index), [])
        return {**source_view(c), "cited": bool(markers), "markers": markers}

    yield {
        "type": "answer",
        "patient_response": toned["patient_response"],
        "doctor_questions": toned["doctor_questions"],
        "citations": [_citation_view(c) for c in ans["citations"]],
        "sources": [_answer_source_view(c) for c in result.chunks],
        "flagged_gaps": checked["flagged_gaps"],
        "confidence": checked["confidence"],
        "disclaimer": DEMO_DISCLAIMER,
    }
    yield {"type": "done"}


def build_prep_sheet(
    conversation_history: list[dict],
    document_context: str,
    patient_concerns: list[str],
    *,
    llm: LLMProvider,
    settings: Settings | None = None,
) -> PrepSheet:
    s = settings or get_settings()
    return generate_prep_sheet(
        conversation_history,
        document_context,
        patient_concerns,
        llm=llm,
        model=s.llm_model_strong,
    )
