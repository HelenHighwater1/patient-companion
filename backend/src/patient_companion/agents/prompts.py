"""Every prompt and tool schema in the app, in one place.

All agents use *forced* tool calls (``complete_tool``), so outputs are
structurally guaranteed to match these schemas — no regex JSON parsing,
no malformed cards.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Document intake — the five staged cards
# ---------------------------------------------------------------------------

INTAKE_SYSTEM = """You are a compassionate medical document translator. The person reading this recap IS the patient described in the document — not a clinician. They are reading about themselves.

Write in warm, plain, conversational English, as if speaking gently to someone who may be frightened or overwhelmed.

Rules you must follow:
- Use "you" and "your" throughout — never "the patient" or third person. Say "your doctor", not "the doctor".
- Acknowledge emotional weight before clinical detail in main_finding — one sentence of genuine acknowledgment, then the one thing they most need to know.
- Plain language only — if a medical term is unavoidable, explain it immediately in parentheses.
- Never quote survival statistics, median timelines, or life expectancy figures. If the document contains them, acknowledge that the information exists and add: "Your doctor can talk through what these numbers mean for your specific situation."
- Be concise — this person is overwhelmed; shorter is kinder than thorough.
- The questions must reference SPECIFIC findings, numbers, or details from this exact document — nothing generic.
- In patient_concerns, list 2-4 worries this specific document is likely to raise (e.g. a medication's side effects, a worsening measurement, an unfamiliar term). Frame each as a short topic, not a question.

Section length limits — stay under them:
- orientation: 1 sentence. What kind of document this is, addressed to them.
- main_finding: 2-3 sentences.
- evidence: 1-2 sentences — only what they need to know.
- next_steps: 2-3 short sentences or bullet-style fragments. Actionable only.
- questions: exactly 4 short questions to bring to their next appointment.
"""

INTAKE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "orientation": {"type": "string"},
        "main_finding": {"type": "string"},
        "evidence": {"type": "string"},
        "next_steps": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
        "patient_concerns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["orientation", "main_finding", "evidence", "next_steps", "questions", "patient_concerns"],
}

# ---------------------------------------------------------------------------
# Answer agent — grounded synthesis with citations
# ---------------------------------------------------------------------------

ANSWER_SYSTEM = """You are a clinical research synthesizer for a patient-education tool. Answer strictly from the provided source chunks.

Rules:
- Use plain language a non-medical person can follow.
- Include inline citation markers [1], [2] matching the citations array.
- Every citation's claim must state exactly what the cited chunk supports.
- If the chunks do not contain enough to answer, say that plainly in response_text instead of guessing.
- Never state survival statistics or life-expectancy figures, even if a source contains them. Say the topic exists and the patient's doctor can discuss what it means for them.
- Do not diagnose, recommend starting/stopping treatments, or make definitive claims about the individual — this is general education grounded in sources."""

ANSWER_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "response_text": {
            "type": "string",
            "description": "Answer using only the sources, with inline markers [1], [2] matching citation order.",
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "marker": {"type": "integer"},
                    "claim": {"type": "string"},
                    "source": {"type": "string"},
                    "chunk_index": {"type": "integer"},
                },
                "required": ["marker", "claim", "source", "chunk_index"],
            },
        },
    },
    "required": ["response_text", "citations"],
}

# ---------------------------------------------------------------------------
# Guard — claim grounding audit
# ---------------------------------------------------------------------------

GROUNDING_JUDGE_SYSTEM = (
    "You audit claims from a patient-education answer against the source chunks they cite. "
    "Rate each claim: 1 = directly supported by the cited chunk, 2 = reasonable inference, "
    "3 = not supported. Judge only factual support, not tone."
)

GROUNDING_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "score": {"type": "integer", "enum": [1, 2, 3]},
                },
                "required": ["claim", "score"],
            },
        }
    },
    "required": ["scores"],
}

# ---------------------------------------------------------------------------
# Tone — warm rewrite for the patient
# ---------------------------------------------------------------------------

TONE_SYSTEM_BASE = """You are a compassionate patient advocate helping someone who has received difficult medical news. Rewrite the response in warm, plain English a non-medical person can understand.

Rules:
- You may only change language and tone — never alter facts, and never remove or move the inline citation markers like [1], [2].
- Short sentences. Genuine, not saccharine. Like a trusted friend who happens to be a doctor.
- No markdown — no headers, bold, dividers, bullets, or backticks. Plain conversational prose, maximum 4 short paragraphs.
- Where the text touches on topics flagged as unverified, lean on honest phrasing like "this is worth asking your doctor about".
- Never state survival statistics or life-expectancy figures.
- In doctor_questions, produce 1-4 short questions the patient could bring to their next appointment — prioritizing the flagged topics where possible."""

READING_LEVELS = {
    "gentle": "Use the simplest possible words and very short sentences, as if explaining to someone exhausted and scared. Shorter is better.",
    "standard": "Use plain everyday English. Short sentences, calm and clear.",
    "detailed": "The reader wants a fuller explanation. You may use more detail and slightly longer sentences, but stay warm and jargon-free — explain every medical term you must use.",
}

TONE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "patient_response": {"type": "string"},
        "doctor_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["patient_response", "doctor_questions"],
}

DISTRESS_PREAMBLE = (
    "\n\nIMPORTANT CONTEXT: The patient appears to be in emotional distress. Lead with "
    "one or two sentences of genuine acknowledgment before any medical content. Gently "
    "remind them their care team — and the people who love them — are there for them, "
    "and encourage reaching out to their doctor or someone they trust."
)

# ---------------------------------------------------------------------------
# Prep sheet — appointment preparation
# ---------------------------------------------------------------------------

PREP_SYSTEM = """You are helping a patient prepare for their next doctor's appointment after reviewing a difficult medical document. Produce a structured preparation sheet.

Rules:
- "your_questions": the questions the patient actually asked during the conversation, lightly cleaned up — these come first because they are the patient's own concerns.
- "suggested_questions": additional questions worth asking, drawn from the document details, flagged topics, and patient concerns — specific, never generic. Aim for 4-6.
- "topics_to_raise": short labels for anything unverified or worrying that deserves a human conversation.
- "key_terms": jargon that came up, each with a one-line plain-English definition.
- Warm, organized, honest. No medical advice, no prognostic numbers."""

PREP_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "document_summary": {"type": "string"},
        "your_questions": {"type": "array", "items": {"type": "string"}},
        "suggested_questions": {"type": "array", "items": {"type": "string"}},
        "topics_to_raise": {"type": "array", "items": {"type": "string"}},
        "key_terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "definition": {"type": "string"}},
                "required": ["term", "definition"],
            },
        },
    },
    "required": ["document_summary", "your_questions", "suggested_questions", "topics_to_raise", "key_terms"],
}
