"""Query rewriting + scope check in a single fast-model call.

Returns query variants to embed (standalone, clinical rephrase, HyDE-style
passage) plus an ``in_scope`` flag so off-topic questions are refused before
any retrieval spend.
"""

from __future__ import annotations

import logging
from typing import Any

from patient_companion.providers.base import LLMProvider

logger = logging.getLogger(__name__)

RETRIEVAL_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "1-3 retrieval query variants: the standalone question, a clinical "
            "rephrasing, and optionally a short textbook-style passage that would answer it.",
        },
        "in_scope": {
            "type": "boolean",
            "description": "True if the question is about the patient's condition, care, symptoms, "
            "treatment, daily life with the disease, or understanding their medical documents.",
        },
        "scope_reason": {"type": "string"},
    },
    "required": ["queries", "in_scope"],
}

_SYSTEM = (
    "You are the retrieval planner for a medical patient-companion tool whose knowledge base "
    "covers {disease} and closely related care topics. Given the latest user message and recent "
    "conversation, produce retrieval query variants and decide whether the question is in scope. "
    "In scope: the disease, its symptoms, progression, treatments, breathing/feeding/mobility, "
    "caregiving, emotional coping, understanding their documents, and preparing for appointments. "
    "Out of scope: unrelated medical conditions, general knowledge, chit-chat, or anything where "
    "no reliable source in a disease-specific knowledge base could help."
)


def plan_retrieval(
    question: str,
    conversation_history: list[dict] | None,
    *,
    llm: LLMProvider,
    model: str,
    disease_label: str = "ALS (amyotrophic lateral sclerosis)",
) -> dict[str, Any]:
    """Return {queries: [...], in_scope: bool, scope_reason: str}."""
    q = (question or "").strip()
    if not q:
        return {"queries": [], "in_scope": False, "scope_reason": "empty"}

    hist_lines = []
    for ex in (conversation_history or [])[-6:]:
        q_prev = ex.get("question") or ex.get("message") or ""
        a_prev = ex.get("patient_response") or ex.get("answer") or ""
        if q_prev:
            hist_lines.append(f"User: {q_prev}\nAssistant: {a_prev[:400]}")
    hist_block = "\n".join(hist_lines) if hist_lines else "(none)"

    payload = llm.complete_tool(
        system=_SYSTEM.format(disease=disease_label),
        user=f"Conversation context:\n{hist_block}\n\nLatest user message:\n{q}",
        tool_name="emit_retrieval_plan",
        tool_description="Emit retrieval query variants and the in-scope decision.",
        input_schema=RETRIEVAL_PLAN_SCHEMA,
        model=model,
        max_tokens=500,
    )

    queries = [s for s in (payload.get("queries") or []) if isinstance(s, str) and s.strip()]
    if q not in queries:
        queries.insert(0, q)
    return {
        "queries": queries[:4] or [q],
        "in_scope": bool(payload.get("in_scope", True)),
        "scope_reason": payload.get("scope_reason", ""),
    }
