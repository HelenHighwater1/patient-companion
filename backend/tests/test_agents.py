from patient_companion.agents.distress import is_distressed
from patient_companion.agents.intake import card_events, summarize_document
from patient_companion.agents.prep import generate_prep_sheet
from patient_companion.config import get_settings
from patient_companion.providers import get_llm


def _llm():
    return get_llm()


def _model():
    return get_settings().llm_model_strong


def test_intake_returns_five_sections_and_concerns():
    sections = summarize_document(
        "Clinical note: EMG findings consistent with ALS. Started riluzole. "
        "Follow-up pulmonary function test in 4 weeks.",
        llm=_llm(),
        model=_model(),
    )
    assert sections.orientation
    assert sections.main_finding
    assert len(sections.questions) == 4
    assert sections.patient_concerns


def test_card_events_ordered_and_labelled():
    sections = summarize_document("Doc text here.", llm=_llm(), model=_model())
    events = card_events(sections)
    cards = [e for e in events if e["type"] == "card"]
    assert [c["index"] for c in cards] == [0, 1, 2, 3, 4]
    assert cards[-1]["key"] == "questions"
    assert isinstance(cards[-1]["body"], list)


def test_intake_empty_document():
    sections = summarize_document("", llm=_llm(), model=_model())
    assert "empty" in sections.main_finding.lower() or "trouble" in sections.orientation.lower()


def test_prep_sheet_schema():
    sheet = generate_prep_sheet(
        [{"question": "What is riluzole?", "patient_response": "A medicine that may slow ALS."}],
        "Doc summary",
        ["medication side effects"],
        llm=_llm(),
        model=_model(),
    )
    assert sheet.suggested_questions
    assert sheet.your_questions


def test_distress_detection():
    assert is_distressed("I'm really scared about what this means")
    assert is_distressed("I can't cope with this")
    assert not is_distressed("What does riluzole do?")
