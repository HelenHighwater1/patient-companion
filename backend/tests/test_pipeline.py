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


def test_document_summary_failed_calls_stay_out_of_context():
    class _FailLLM:
        def complete_tool(self, **kw):
            raise RuntimeError("boom")

        def complete(self, **kw):
            return ""

    events = _drain(
        stream_document_summary(
            "Clinic note: EMG consistent with ALS.",
            llm=_FailLLM(),
            settings=get_settings(),
        )
    )
    assert sum(1 for e in events if e["type"] == "card") == 5
    done = events[-1]
    assert done["document_context"] == ""
    assert done["patient_concerns"] == []
    first_card = next(e for e in events if e["type"] == "card")
    assert "couldn't" in first_card["body"]


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

    retrieval = next(e for e in events if e["type"] == "retrieval")
    assert events.index(retrieval) < events.index(answer)
    assert retrieval["query_variants"]
    assert retrieval["gate"]["passed"] is True
    assert retrieval["counts"]["returned"] == len(retrieval["sources"])
    assert all(s["excerpt"] for s in retrieval["sources"])

    cited = [s for s in answer["sources"] if s["cited"]]
    assert cited and all(s["markers"] for s in cited)
    cited_keys = {(s["source"], s["chunk_index"]) for s in cited}
    for c in answer["citations"]:
        assert (c["source"], c["chunk_index"]) in cited_keys
        assert c["grounding"]["checked"] is True


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
    retrieval = next(e for e in events if e["type"] == "retrieval")
    assert retrieval["refused"] is True
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
