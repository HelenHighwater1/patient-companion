"""Deterministic mock providers for tests, CI, and demo-without-keys.

MockLLM returns schema-valid payloads for every tool the agents use, so the
entire pipeline (intake, retrieve, answer, ground, prep) is exercised
end-to-end offline. MockEmbedder produces stable hash-based vectors so
lexically similar text retrieves correctly.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_DIMS = 256

_ALS_TERMS = (
    "als",
    "amyotrophic",
    "lou gehrig",
    "motor neuron",
    "riluzole",
    "edaravone",
    "breath",
    "ventilat",
    "swallow",
    "symptom",
    "diagnos",
    "twitch",
    "weakness",
    "fasciculation",
    "feeding tube",
    "speech",
    "caregiver",
    "prognos",
    "wheelchair",
)


def _last_user_question(user: str) -> str:
    m = re.search(r"Latest user message:\s*(.+?)(?:\n\n|$)", user, re.DOTALL)
    return (m.group(1).strip() if m else user).strip()


class MockLLM:
    """Returns deterministic, schema-valid tool payloads keyed on tool name."""

    def complete_tool(
        self,
        *,
        system: str,
        user: str,
        tool_name: str,
        tool_description: str,
        input_schema: dict[str, Any],
        model: str,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return {}
        return handler(user)

    def complete(self, *, system: str, user: str, model: str, max_tokens: int = 1024) -> str:
        return "This is a mock response for testing."

    # -- Tool payload builders -------------------------------------------------

    def _tool_emit_retrieval_plan(self, user: str) -> dict[str, Any]:
        question = _last_user_question(user)
        lowered = question.lower()
        in_scope = any(t in lowered for t in _ALS_TERMS)
        return {
            "queries": [question, f"clinical aspects of {question}"],
            "in_scope": in_scope,
            "scope_reason": "mock scope check",
        }

    def _tool_emit_document_sections(self, user: str) -> dict[str, Any]:
        m = re.search(r"Document text:\s*(.+)", user, re.DOTALL)
        doc = (m.group(1) if m else user).strip()
        first_line = doc.splitlines()[0][:120] if doc else "your document"
        return {
            "orientation": f"This is a medical document ({first_line}).",
            "main_finding": "I know this may be difficult to read. The document describes findings "
            "about your condition that your care team will walk you through.",
            "evidence": "The document records test results and clinical observations.",
            "next_steps": "Follow up with your care team and bring your questions.",
            "questions": [
                "What do these findings mean for my day-to-day life?",
                "Are there treatments that could slow progression?",
                "What symptoms should I watch for next?",
                "Who is on my care team and how do I reach them?",
            ],
            "patient_concerns": ["Understanding what the diagnosis means", "Planning next steps"],
        }

    def _tool_emit_answer(self, user: str) -> dict[str, Any]:
        # Parse "source=X chunk_index=N" pairs the prompt embeds per chunk.
        pairs = re.findall(r"source=([\w.\-]+)\s+chunk_index=(\d+)", user)
        citations = [
            {
                "marker": n + 1,
                "claim": f"Mock claim supported by chunk {n + 1}",
                "source": src,
                "chunk_index": int(idx),
            }
            for n, (src, idx) in enumerate(pairs[:3])
        ]
        markers = " ".join(f"[{c['marker']}]" for c in citations)
        return {
            "patient_response": f"Based on the provided sources, here is a grounded answer. {markers}",
            "citations": citations,
            "doctor_questions": [
                "Could you explain what this means for my treatment plan?",
                "What should I watch for between now and our next visit?",
            ],
        }

    def _tool_emit_grounding_scores(self, user: str) -> dict[str, Any]:
        m = re.search(r"Mechanical check results:\s*(\[.*?\])", user, re.DOTALL)
        scores = []
        if m:
            try:
                for item in json.loads(m.group(1)):
                    scores.append({"claim": item.get("claim", ""), "score": 1})
            except json.JSONDecodeError:
                pass
        return {"scores": scores}

    def _tool_emit_prep_sheet(self, user: str) -> dict[str, Any]:
        return {
            "document_summary": "We discussed your medical document and your questions about it.",
            "your_questions": ["What do these findings mean for me?"],
            "suggested_questions": [
                "What are my treatment options?",
                "How will we track progression?",
                "What support services are available?",
            ],
            "topics_to_raise": ["Follow-up planning"],
            "key_terms": [
                {"term": "ALS", "definition": "A condition affecting nerve cells that control muscles."}
            ],
        }


class MockEmbedder:
    """Deterministic bag-of-hashed-token embeddings (256 dims)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vec = [0.0] * _DIMS
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            vec[h % _DIMS] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]
