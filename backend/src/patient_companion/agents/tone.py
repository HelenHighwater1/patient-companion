"""Tone agent: verified answer → warm, patient-readable prose + questions."""

from __future__ import annotations

from patient_companion.agents.prompts import (
    DISTRESS_PREAMBLE,
    READING_LEVELS,
    TONE_SYSTEM_BASE,
    TONE_TOOL_SCHEMA,
)
from patient_companion.providers.base import LLMProvider
from patient_companion.schemas import ReadingLevel


def apply_tone(
    verified_response: str,
    flagged_gaps: list[str],
    *,
    llm: LLMProvider,
    model: str,
    reading_level: ReadingLevel = "standard",
    distress: bool = False,
) -> dict:
    """Return {patient_response, doctor_questions}."""
    system = TONE_SYSTEM_BASE + "\n\nReading level: " + READING_LEVELS.get(
        reading_level, READING_LEVELS["standard"]
    )
    if distress:
        system += DISTRESS_PREAMBLE

    gaps = ""
    if flagged_gaps:
        gaps = "\n\nTopics to gently suggest they raise with their doctor:\n" + "\n".join(
            f"- {g}" for g in flagged_gaps
        )
    user = (
        f"Text to rewrite:\n\n{verified_response}{gaps}\n\n"
        "Call emit_tone with patient_response and doctor_questions."
    )

    payload = llm.complete_tool(
        system=system,
        user=user,
        tool_name="emit_tone",
        tool_description="Emit the patient-friendly rewrite and suggested questions.",
        input_schema=TONE_TOOL_SCHEMA,
        model=model,
        max_tokens=1000,
    )
    return {
        "patient_response": (payload.get("patient_response") or "").strip() or verified_response.strip(),
        "doctor_questions": [q for q in payload.get("doctor_questions") or [] if str(q).strip()],
    }
