"""Document intake agent: document text → five staged cards.

Each section is produced by its own small forced-tool call, in card order,
so the first card can stream to the patient quickly while later sections
are still being generated. Forced tool calls keep the structure incapable
of being malformed — the old failure mode (regex-parsing free-text JSON)
is gone by design.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from patient_companion.agents.prompts import INTAKE_SYSTEM, INTAKE_TOOL_SCHEMA
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import CARD_LABELS, DocumentSections

logger = logging.getLogger(__name__)

_MAX_DOC_CHARS = 60_000

# Calls fired in parallel on upload: the first pair of cards lands after the
# smaller call while the others generate concurrently. Splitting the tail
# into two calls shortens the wall-clock long pole — the single 1400-token
# call used to finish well after everything else. Each group is emitted as
# separate card events — the frontend paces the reveal either way.
_SECTION_GROUPS: list[tuple[tuple[str, ...], int]] = [
    (("orientation", "main_finding"), 700),
    (("evidence", "next_steps"), 800),
    (("questions", "patient_concerns"), 800),
]

# Per-section fallbacks so one failed call can't take down the whole recap.
# Each reads as an explicit failure — never as a statement about the
# document — and failed sections are kept out of document_context so
# follow-up answers and the prep sheet stay grounded in real content.
_FALLBACKS: dict[str, str | list[str]] = {
    "orientation": "This looks like a medical document, "
    "but we couldn't read it clearly.",
    "main_finding": "We couldn't summarize the main finding — "
    "your care team can walk you through it.",
    "evidence": "We couldn't summarize what the tests showed — "
    "ask your care team to explain the results.",
    "next_steps": "We couldn't read the next steps clearly — "
    "please confirm them with your care team.",
    "questions": [
        "What does this document mean for my day-to-day life?",
        "What should I watch for between now and my next visit?",
        "Who should I contact if something changes?",
    ],
    "patient_concerns": [],
}


def _coerce(key: str, value: Any) -> tuple[str | list[str], bool]:
    """Validate one section's value.

    Returns ``(display_value, from_model)`` — the flag lets callers keep
    fallback wording out of anything treated as document content.
    """
    fallback = _FALLBACKS[key]
    if isinstance(fallback, list):
        items = (
            [s.strip() for s in value if isinstance(s, str) and s.strip()]
            if isinstance(value, list)
            else []
        )
        if items:
            return items[:4] if key == "questions" else items, True
        return fallback, False
    if isinstance(value, str) and value.strip():
        return value.strip(), True
    return fallback, False


def _section_payload(
    prompt: str,
    keys: tuple[str, ...],
    max_tokens: int,
    *,
    llm: LLMProvider,
    model: str,
) -> dict[str, Any]:
    """One forced-tool call producing a group of sections; {} on failure."""
    schema = {
        "type": "object",
        "properties": {k: INTAKE_TOOL_SCHEMA["properties"][k] for k in keys},
        "required": list(keys),
    }
    try:
        return llm.complete_tool(
            system=INTAKE_SYSTEM,
            user=prompt
            + f"Produce the {' and '.join(keys)} section(s) of the recap "
            "for this patient.",
            tool_name="emit_document_sections",
            tool_description="Emit patient-facing recap section(s).",
            input_schema=schema,
            model=model,
            max_tokens=max_tokens,
        )
    except Exception:
        logger.exception("intake call failed for %s", " and ".join(keys))
        return {}


def iter_document_sections(
    document_text: str, *, llm: LLMProvider, model: str
) -> Iterator[tuple[str, str | list[str], bool]]:
    """Yield ``(section_key, value, from_model)`` as each call completes.

    The group calls run in parallel but are yielded in card order: the
    first pair lands after its short call while the bigger call behind it
    is still generating the remaining sections.
    """
    text = (document_text or "").strip()
    if not text:
        yield "orientation", "I couldn't read that document.", True
        yield "main_finding", (
            "The document appears to be empty or unreadable. "
            "Please try a different file."
        ), True
        yield "evidence", "", False
        yield "next_steps", "", False
        yield "questions", [], False
        return
    if len(text) > _MAX_DOC_CHARS:
        text = text[:_MAX_DOC_CHARS]
        logger.info("document truncated to %d chars for intake", _MAX_DOC_CHARS)

    prompt = f"Document text:\n\n{text}\n\n"
    with ThreadPoolExecutor(max_workers=len(_SECTION_GROUPS)) as pool:
        futures = [
            (
                keys,
                pool.submit(
                    _section_payload, prompt, keys, max_tokens, llm=llm, model=model
                ),
            )
            for keys, max_tokens in _SECTION_GROUPS
        ]
        for keys, future in futures:
            payload = future.result()
            for key in keys:
                value, from_model = _coerce(key, payload.get(key))
                yield key, value, from_model


def summarize_document(
    document_text: str, *, llm: LLMProvider, model: str
) -> DocumentSections:
    """Non-streaming variant: drain every section call into one object."""
    values = {
        k: v
        for k, v, _ in iter_document_sections(document_text, llm=llm, model=model)
    }
    return DocumentSections.model_validate(values)


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
