"""Answer agent: warm grounded synthesis from retrieved chunks with citations.

The patient-facing text is written in one pass — the grounding audit then
checks the exact wording the patient reads, rather than a draft that a
separate rewrite step could silently distort.
"""

from __future__ import annotations

from patient_companion.agents.prompts import (
    ANSWER_SYSTEM,
    ANSWER_TOOL_SCHEMA,
    DISTRESS_PREAMBLE,
    READING_LEVELS,
)
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import Chunk, Citation, ReadingLevel

_MAX_DOC_CONTEXT_CHARS = 8_000


def _chunks_to_text(chunks: list[Chunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[Chunk {i}] source={c.source} chunk_index={c.chunk_index} "
            f"title={c.title or ''}\n{c.document}"
        )
    return "\n\n---\n\n".join(parts)


def answer_question(
    question: str,
    chunks: list[Chunk],
    *,
    llm: LLMProvider,
    model: str,
    document_context: str | None = None,
    reading_level: ReadingLevel = "standard",
    distress: bool = False,
) -> dict:
    """Return {patient_response, doctor_questions, citations, chunks_used}."""
    system = ANSWER_SYSTEM + "\n\nReading level: " + READING_LEVELS.get(
        reading_level, READING_LEVELS["standard"]
    )
    if distress:
        system += DISTRESS_PREAMBLE

    doc_block = ""
    if document_context and document_context.strip():
        doc_block = (
            "\n\nOptional context from the patient's own document "
            "(inform your answer, but do not cite it — only cite source chunks):\n"
            + document_context.strip()[:_MAX_DOC_CONTEXT_CHARS]
        )
    user = f"Source chunks:\n\n{_chunks_to_text(chunks)}{doc_block}\n\nQuestion:\n{question.strip()}"

    payload = llm.complete_tool(
        system=system,
        user=user,
        tool_name="emit_answer",
        tool_description="Emit the patient answer, its citations, and suggested doctor questions.",
        input_schema=ANSWER_TOOL_SCHEMA,
        model=model,
        max_tokens=1400,
    )

    response = (payload.get("patient_response") or "").strip()
    citations = [
        Citation.model_validate(c) for c in payload.get("citations") or [] if isinstance(c, dict)
    ]
    if not response:
        response = (
            "I couldn't find that in the sources I have here. "
            "It's worth asking your care team — they can point you to the right information."
        )
        citations = []

    used = {(c.source, c.chunk_index) for c in citations}
    chunks_used = [c for c in chunks if (c.source, c.chunk_index) in used] or chunks
    return {
        "patient_response": response,
        "doctor_questions": [
            q for q in payload.get("doctor_questions") or [] if str(q).strip()
        ],
        "citations": citations,
        "chunks_used": chunks_used,
    }
