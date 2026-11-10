"""Answer agent: grounded synthesis from retrieved chunks with citations."""

from __future__ import annotations

from patient_companion.agents.prompts import ANSWER_SYSTEM, ANSWER_TOOL_SCHEMA
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import Chunk, Citation

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
) -> dict:
    """Return {response, citations, chunks_used}."""
    doc_block = ""
    if document_context and document_context.strip():
        doc_block = (
            "\n\nOptional context from the patient's own document "
            "(inform your answer, but do not cite it — only cite source chunks):\n"
            + document_context.strip()[:_MAX_DOC_CONTEXT_CHARS]
        )
    user = f"Source chunks:\n\n{_chunks_to_text(chunks)}{doc_block}\n\nQuestion:\n{question.strip()}"

    payload = llm.complete_tool(
        system=ANSWER_SYSTEM,
        user=user,
        tool_name="emit_answer",
        tool_description="Emit the grounded answer and its citations.",
        input_schema=ANSWER_TOOL_SCHEMA,
        model=model,
        max_tokens=1200,
    )

    response = (payload.get("response_text") or "").strip()
    citations = [Citation.model_validate(c) for c in payload.get("citations") or [] if isinstance(c, dict)]
    if not response:
        response = "This information was not found in the source documents."
        citations = []

    used = {(c.source, c.chunk_index) for c in citations}
    chunks_used = [c for c in chunks if (c.source, c.chunk_index) in used] or chunks
    return {"response": response, "citations": citations, "chunks_used": chunks_used}
