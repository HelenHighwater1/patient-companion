"""Prep agent: conversation + document → printable appointment prep sheet.

The patient's own chat questions come first in the output — the sheet exists
to make sure *their* concerns make it into the room.
"""

from __future__ import annotations

import logging

from patient_companion.agents.prompts import PREP_SYSTEM, PREP_TOOL_SCHEMA
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import PrepSheet

logger = logging.getLogger(__name__)


def generate_prep_sheet(
    conversation_history: list[dict],
    document_context: str,
    patient_concerns: list[str],
    *,
    llm: LLMProvider,
    model: str,
) -> PrepSheet:
    history_text = ""
    for i, ex in enumerate(conversation_history[-12:], 1):
        q = ex.get("question", "")
        a = ex.get("patient_response") or ex.get("answer") or ""
        history_text += f"\n--- Exchange {i} ---\nQ: {q}\nA: {a}\n"
    if not history_text:
        history_text = "\n(no follow-up questions asked yet)"

    concerns = "\n".join(f"- {c}" for c in patient_concerns) or "(none recorded)"
    user = (
        f"Conversation history:{history_text}\n\n"
        f"Context about the patient's document:\n{document_context[:6000] or 'Not provided.'}\n\n"
        f"Concerns likely raised by the document:\n{concerns}\n\n"
        "Produce the appointment preparation sheet."
    )

    payload = llm.complete_tool(
        system=PREP_SYSTEM,
        user=user,
        tool_name="emit_prep_sheet",
        tool_description="Emit the structured appointment prep sheet.",
        input_schema=PREP_TOOL_SCHEMA,
        model=model,
        max_tokens=2000,
    )
    try:
        return PrepSheet.model_validate(payload)
    except Exception as e:
        logger.error("prep sheet validation failed: %s | payload=%s", e, payload)
        return PrepSheet(document_summary="We weren't able to build the prep sheet this time.")
