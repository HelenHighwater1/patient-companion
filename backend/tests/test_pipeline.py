from patient_companion.agents.pipeline import (
    build_prep_sheet,
    stream_answer,
    stream_document_summary,
)
from patient_companion.config import get_settings
from patient_companion.providers import get_embedder, get_llm


def _drain(events):
    return list(events)


def test_document_summary_streams_five_cards():
    events = _drain(
        stream_document_summary(
            "Clinic note: EMG consistent with ALS. Riluzole started.",
            llm=get_llm(),
            settings=get_settings(),
        )
    )
    types = [e["type"] for e in events]
    assert types[0] == "status"
    assert types.count("card") == 5
    assert types[-1] == "done"
    done = events[-1]
    assert done["document_context"]
    assert done["patient_concerns"]


def test_answer_pipeline_events(retriever):
    events = _drain(
        stream_answer(
            "How does ALS affect breathing?",
            [],
            None,
            "standard",
            retriever=retriever,
            llm=get_llm(),
            embedder=get_embedder(),
            settings=get_settings(),
        )
    )
    stages = [e.get("stage") for e in events if e["type"] == "status"]
    assert stages == ["searching", "answering", "checking", "rewriting"]
    answer = next(e for e in events if e["type"] == "answer")
    assert answer["patient_response"]
    assert answer["sources"]
    assert events[-1]["type"] == "done"


def test_answer_pipeline_refusal(retriever):
    events = _drain(
        stream_answer(
            "What is the capital of France?",
            [],
            None,
            "standard",
            retriever=retriever,
            llm=get_llm(),
            embedder=get_embedder(),
        )
    )
    assert events[0]["type"] == "status"
    refusal = next(e for e in events if e["type"] == "refusal")
    assert "sources" in refusal["message"] or "safely" in refusal["message"]
    assert events[-1]["type"] == "done"


def test_prep_sheet_via_pipeline():
    sheet = build_prep_sheet(
        [{"question": "q", "patient_response": "a"}],
        "ctx",
        [],
        llm=get_llm(),
        settings=get_settings(),
    )
    assert sheet.suggested_questions
