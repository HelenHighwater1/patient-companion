"""Shared data models for the pipeline and API.

These are the contracts between retrieval, agents, the FastAPI layer, and
(via SSE events) the frontend. Keep them small and explicit.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ReadingLevel = Literal["gentle", "standard", "detailed"]


# --- Retrieval -------------------------------------------------------------


class Chunk(BaseModel):
    """One retrievable unit of knowledge-base text with provenance."""

    document: str
    source: str
    chunk_index: int = 0
    relevance: float = 0.0
    title: str | None = None
    section: str | None = None
    section_path: str | None = None
    source_id: str | None = None
    url: str | None = None
    year: int | None = None
    source_type: str | None = None
    dense_cosine: float | None = None
    fusion_score: float | None = None
    rerank_score: float | None = None


class Citation(BaseModel):
    marker: int
    claim: str
    source: str
    chunk_index: int


# --- Document intake ---------------------------------------------------------


class DocumentSections(BaseModel):
    """The five staged cards produced when a document is uploaded."""

    orientation: str = ""
    main_finding: str = ""
    evidence: str = ""
    next_steps: str = ""
    questions: list[str] = Field(default_factory=list)
    # Worries the document is likely to raise for this patient. Folded into
    # the prep sheet so the patient's concerns are never lost.
    patient_concerns: list[str] = Field(default_factory=list)


CARD_LABELS: list[tuple[str, str]] = [
    ("orientation", "What this document is"),
    ("main_finding", "The main finding"),
    ("evidence", "What the tests showed"),
    ("next_steps", "What happens next"),
    ("questions", "Questions to bring to your appointment"),
]


class CardEvent(BaseModel):
    type: Literal["card"] = "card"
    index: int
    key: str
    label: str
    body: str | list[str]


# --- Q&A pipeline ------------------------------------------------------------


class ConversationTurn(BaseModel):
    question: str
    answer: str = ""


class AnswerResult(BaseModel):
    """Final, tone-adjusted answer plus everything the UI needs to show."""

    patient_response: str
    doctor_questions: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    flagged_gaps: list[str] = Field(default_factory=list)
    verified_response: str = ""
    confidence: list[dict[str, Any]] = Field(default_factory=list)


class PrepSheet(BaseModel):
    """Printable appointment-preparation sheet."""

    document_summary: str = ""
    your_questions: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    topics_to_raise: list[str] = Field(default_factory=list)
    key_terms: list[dict[str, str]] = Field(default_factory=list)


# --- API payloads --------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str | None = None
    input_type: Literal["question", "document"] = "question"
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    document_context: str | None = None
    document_text: str | None = None
    filename: str | None = None
    reading_level: ReadingLevel = "standard"


class PrepSheetRequest(BaseModel):
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    document_context: str = ""
    patient_concerns: list[str] = Field(default_factory=list)
    reading_level: ReadingLevel = "standard"


class SampleDocument(BaseModel):
    filename: str
    title: str
    file_type: str


DEMO_DISCLAIMER = (
    "This is a demo only — do not enter real personal health information. "
    "It is not medical advice. Always talk with your licensed clinician."
)
