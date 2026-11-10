"""Pipeline orchestration.

Each entry point yields plain-dict events — the server layer serializes
them to SSE. Nothing here knows about HTTP.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from patient_companion.agents.answer import answer_question
from patient_companion.agents.distress import is_distressed
from patient_companion.agents.guard import audit
from patient_companion.agents.intake import card_events, summarize_document
from patient_companion.agents.prep import generate_prep_sheet
from patient_companion.agents.tone import apply_tone
from patient_companion.config import Settings, get_settings
from patient_companion.providers.base import EmbeddingProvider, LLMProvider
from patient_companion.rag.retrieve import Retriever, refusal_message
from patient_companion.schemas import DEMO_DISCLAIMER, Chunk, PrepSheet, ReadingLevel

logger = logging.getLogger(__name__)


def stream_document_summary(
    document_text: str,
    *,
    llm: LLMProvider,
    settings: Settings | None = None,
) -> Iterator[dict[str, Any]]:
    """Document → staged card events → done (with document_context for chat)."""
    s = settings or get_settings()
    yield {"type": "status", "stage": "reading"}
    sections = summarize_document(document_text, llm=llm, model=s.llm_model_strong)
    yield from card_events(sections)
    context = "\n".join(
        part
        for part in [
            sections.orientation,
            sections.main_finding,
            sections.evidence,
            sections.next_steps,
        ]
        if part
    )
    yield {
        "type": "done",
        "document_context": context,
        "patient_concerns": sections.patient_concerns,
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

    def _citation_view(c) -> dict:
        meta = chunk_meta.get((c.source, c.chunk_index)) or Chunk(document="", source=c.source)
        return {
            "marker": c.marker,
            "claim": c.claim,
            "source": c.source,
            "title": meta.title,
            "url": meta.url,
        }

    yield {
        "type": "answer",
        "patient_response": toned["patient_response"],
        "doctor_questions": toned["doctor_questions"],
        "citations": [_citation_view(c) for c in ans["citations"]],
        "sources": [
            {
                "source": c.source,
                "chunk_index": c.chunk_index,
                "title": c.title,
                "url": c.url,
            }
            for c in ans["chunks_used"]
        ],
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
