"""Document intake agent: document text → five staged cards.

Uses a forced tool call, so the card structure can never be malformed —
the old failure mode (regex-parsing free-text JSON) is gone by design.
"""

from __future__ import annotations

import logging

from patient_companion.agents.prompts import INTAKE_SYSTEM, INTAKE_TOOL_SCHEMA
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import CARD_LABELS, DocumentSections

logger = logging.getLogger(__name__)

_MAX_DOC_CHARS = 60_000


def summarize_document(document_text: str, *, llm: LLMProvider, model: str) -> DocumentSections:
    text = (document_text or "").strip()
    if not text:
        return DocumentSections(
            orientation="I couldn't read that document.",
            main_finding="The document appears to be empty or unreadable. "
            "Please try a different file.",
        )
    if len(text) > _MAX_DOC_CHARS:
        text = text[:_MAX_DOC_CHARS]
        logger.info("document truncated to %d chars for intake", _MAX_DOC_CHARS)

    payload = llm.complete_tool(
        system=INTAKE_SYSTEM,
        user=f"Document text:\n\n{text}\n\nProduce the five-section recap for this patient.",
        tool_name="emit_document_sections",
        tool_description="Emit the five-section patient recap.",
        input_schema=INTAKE_TOOL_SCHEMA,
        model=model,
        max_tokens=1400,
    )
    try:
        sections = DocumentSections.model_validate(payload)
    except Exception as e:
        logger.error("intake payload failed validation: %s | payload=%s", e, payload)
        return DocumentSections(
            orientation="We had trouble reading this document.",
            main_finding="Something went wrong while analyzing your document. "
            "Please try again, or bring it to your care team directly.",
        )
    sections.questions = [q for q in sections.questions if q.strip()][:4]
    return sections


def card_events(sections: DocumentSections) -> list[dict]:
    """Convert sections into the ordered card events the frontend renders."""
    events: list[dict] = []
    for i, (key, label) in enumerate(CARD_LABELS):
        body: str | list[str] = getattr(sections, key)
        events.append(
            {"type": "card", "index": i, "key": key, "label": label, "body": body}
        )
    if sections.patient_concerns:
        events.append({"type": "concerns", "items": sections.patient_concerns})
    return events
